from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
import os
from config import Config
from utils import get_db, query_user_by_username, create_user, cache
from utils import fetch_power_data_and_summarize 
import datetime
import requests

app = Flask(__name__)
app.config.from_object(Config)

# Secret key for sessions
app.secret_key = app.config.get("SECRET_KEY", "change_me")

# Initialize cache
cache.init_app(app)

# ----------------------
# --- Helpers ----------
# ----------------------
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

def validate_coordinates(lat, lon):
    """Validate latitude and longitude ranges"""
    try:
        lat = float(lat)
        lon = float(lon)
        if not (-90 <= lat <= 90):
            return False, "Latitude must be between -90 and 90"
        if not (-180 <= lon <= 180):
            return False, "Longitude must be between -180 and 180"
        return True, (lat, lon)
    except (ValueError, TypeError):
        return False, "Invalid coordinate format"

# ----------------------
# --- Scoring Logic ----
# ----------------------
def compute_score(lat, lon, power_summary, ndvi=0.2, population=2000,
                  distance_to_roads_km=1.0, water_distance_km=2.0, structure_type="generic"):
    """
    Enhanced scoring logic with structure-type specific weighting
    """
    
    # Extract climate data safely
    mean_temp = power_summary.get("mean_temp")
    mean_precip = power_summary.get("mean_precip")

    # Default safe values if NASA POWER fails
    if mean_temp is None:
        mean_temp = 25.0
    if mean_precip is None:
        mean_precip = 50.0

    # Temperature scoring (optimal range: 18-28°C)
    temp_score = max(0, 100 - abs(mean_temp - 23) * 4)
    
    # Precipitation scoring (optimal: 50-150mm/month)
    if mean_precip < 50:
        precip_score = (mean_precip / 50.0) * 100
    elif mean_precip <= 150:
        precip_score = 100
    else:
        precip_score = max(0, 100 - (mean_precip - 150) * 0.5)
    
    precip_score = min(100, max(0, precip_score))

    # NDVI normalization (0-1 range)
    ndvi_score = min(100, max(0, ndvi * 100))

    # Population handling based on structure type
    if structure_type in ["hospital", "school"]:
        # Higher density preferred for public services
        pop_score = min(100, (population / 10000.0) * 100)
    elif structure_type == "park":
        # Moderate density ideal for parks
        if population < 5000:
            pop_score = (population / 5000.0) * 100
        else:
            pop_score = max(0, 100 - ((population - 5000) / 5000.0) * 20)
    elif structure_type == "water":
        # Water plants need access but not in dense areas
        pop_score = min(100, (population / 7000.0) * 80)
    else:  # house or generic
        # Lower density preferred for residential
        pop_score = max(0, 100 - (population / 10000.0) * 80)

    # Infrastructure distance factors
    road_score = max(0, 100 - distance_to_roads_km * 10)
    
    # Water distance (avoid flood zones)
    if water_distance_km < 0.3:
        water_score = 0  # Too close - flood risk
    elif water_distance_km < 1.0:
        water_score = 50
    else:
        water_score = min(100, 50 + (water_distance_km - 1.0) * 10)

    # Structure-specific weights
    weights = {
        "hospital": {
            "temp": 0.25, "precip": 0.20, "ndvi": 0.10,
            "pop": 0.30, "road": 0.10, "water": 0.05
        },
        "school": {
            "temp": 0.25, "precip": 0.15, "ndvi": 0.15,
            "pop": 0.25, "road": 0.15, "water": 0.05
        },
        "park": {
            "temp": 0.20, "precip": 0.20, "ndvi": 0.35,
            "pop": 0.15, "road": 0.05, "water": 0.05
        },
        "water": {
            "temp": 0.20, "precip": 0.25, "ndvi": 0.10,
            "pop": 0.15, "road": 0.15, "water": 0.15
        },
        "house": {
            "temp": 0.30, "precip": 0.20, "ndvi": 0.20,
            "pop": 0.15, "road": 0.10, "water": 0.05
        }
    }
    
    # Get weights for structure type, default to house
    w = weights.get(structure_type, weights["house"])
    
    # Calculate weighted score
    final_score = (
        w["temp"] * temp_score +
        w["precip"] * precip_score +
        w["ndvi"] * ndvi_score +
        w["pop"] * pop_score +
        w["road"] * road_score +
        w["water"] * water_score
    )

    return round(final_score, 2)

# ----------------------
# --- Routes -----------
# ----------------------
@app.route("/")
def index():
    if "user" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("planner"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            return render_template("login.html", error="Username and password required")
        
        user = query_user_by_username(username)
        if user and check_password_hash(user[2], password):
            session["user"] = username
            session["role"] = user[3]
            session.permanent = True  # Remember session
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required(role="admin")
def admin():
    return render_template("admin.html", user=session.get("user"))

@app.route("/planner")
@login_required(role="planner")
def planner():
    return render_template("planner.html", user=session.get("user"))

@app.route("/static/img/<path:filename>")
def static_img(filename):
    return send_from_directory(os.path.join(app.root_path, "static", "img"), filename)

# ----------------------
# --- API Endpoints ----
# ----------------------
@app.route("/api/power")
@login_required()
def api_power():
    """Fetch raw NASA POWER data for a coordinate"""
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    start = request.args.get("start")
    end = request.args.get("end")
    params = request.args.get("params", "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR")
    
    if not (lat and lon):
        return jsonify({"error": "lat and lon are required"}), 400

    # Validate coordinates
    valid, result = validate_coordinates(lat, lon)
    if not valid:
        return jsonify({"error": result}), 400
    
    lat, lon = result

    # Set default date range if not provided
    if not start or not end:
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=30)
        start = start_dt.strftime("%Y%m%d")
        end = end_dt.strftime("%Y%m%d")

    cache_key = f"power_{lat}_{lon}_{start}_{end}_{params}"
    data = cache.get(cache_key)
    
    if data is None:
        try:
            payload = {
                "latitude": lat,
                "longitude": lon,
                "start": start,
                "end": end,
                "format": "JSON",
                "community": "RE",
                "parameters": params
            }
            
            resp = requests.get(
                app.config["NASA_POWER_BASE"], 
                params=payload, 
                timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
            cache.set(cache_key, data, timeout=60*60)
            
        except requests.exceptions.Timeout:
            return jsonify({"error": "NASA POWER API timeout"}), 504
        except requests.exceptions.RequestException as e:
            print(f"[API_POWER ERROR] Lat:{lat} Lon:{lon} Error:{e}")
            return jsonify({"error": "Failed to fetch data from NASA POWER"}), 500
        except Exception as e:
            print(f"[API_POWER UNEXPECTED ERROR] {e}")
            return jsonify({"error": "Internal server error"}), 500
            
    return jsonify(data)

@app.route("/api/analyze_point")
@login_required()
def api_analyze_point():
    """Analyze a single point (lat, lon) for quick UI calls"""
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    
    if not lat or not lon:
        return jsonify({"error": "lat and lon required"}), 400
    
    try:
        # Validate coordinates
        valid, result = validate_coordinates(lat, lon)
        if not valid:
            return jsonify({"error": result}), 400
        
        lat, lon = result
        
        # Get optional parameters
        start = request.args.get("start", "")
        end = request.args.get("end", "")
        ndvi = float(request.args.get("ndvi", 0.2))
        population = int(request.args.get("population", 2000))
        structure_type = request.args.get("type", "generic")
        road_km = float(request.args.get("road_km", 1.0))
        water_km = float(request.args.get("water_km", 2.0))
        
        # Set default date range if not provided
        if not start or not end:
            end_dt = datetime.date.today()
            start_dt = end_dt - datetime.timedelta(days=30)
            start = start_dt.strftime("%Y%m%d")
            end = end_dt.strftime("%Y%m%d")
        
        # Fetch climate data
        power_summary = {}
        try:
            power_summary = fetch_power_data_and_summarize(lat, lon, start, end)
        except Exception as e:
            print(f"[ANALYZE_POINT POWER ERROR] Lat:{lat} Lon:{lon} Error:{e}")
            # Continue with empty power_summary - scoring will use defaults
        
        # Clamp NDVI to valid range
        ndvi = max(0.0, min(1.0, ndvi))
        population = max(0, population)
        
        # Compute score
        score = compute_score(
            lat, lon, power_summary,
            ndvi=ndvi,
            population=population,
            distance_to_roads_km=road_km,
            water_distance_km=water_km,
            structure_type=structure_type
        )
        
        return jsonify({
            "lat": lat,
            "lon": lon,
            "score": score,
            "power_summary": power_summary,
            "ndvi": ndvi,
            "population": population,
            "structure_type": structure_type,
            "road_km": road_km,
            "water_km": water_km
        })
        
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
    except Exception as e:
        print(f"[ANALYZE_POINT ERROR] {e}")
        return jsonify({"error": "Failed to analyze point"}), 500

@app.route("/api/hotspot_score", methods=["POST"])
@login_required()
def api_hotspot_score():
    """Analyze multiple points and return suitability scores"""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        points = payload.get("points", [])
        start = payload.get("start", "")
        end = payload.get("end", "")

        if not points:
            return jsonify({"error": "No points provided"}), 400
        
        if len(points) > 50:
            return jsonify({"error": "Maximum 50 points allowed per request"}), 400

        # Set default date range
        if not start or not end:
            end_dt = datetime.date.today()
            start_dt = end_dt - datetime.timedelta(days=30)
            start = start_dt.strftime("%Y%m%d")
            end = end_dt.strftime("%Y%m%d")

        results = []
        errors = []
        
        for idx, pt in enumerate(points):
            try:
                lat = pt.get("lat")
                lon = pt.get("lon")
                
                if lat is None or lon is None:
                    errors.append(f"Point {idx}: Missing coordinates")
                    continue
                
                # Validate coordinates
                valid, result = validate_coordinates(lat, lon)
                if not valid:
                    errors.append(f"Point {idx}: {result}")
                    continue
                
                lat, lon = result
                
                # Fetch climate data
                power_summary = {}
                try:
                    power_summary = fetch_power_data_and_summarize(lat, lon, start, end)
                except Exception as e:
                    print(f"[HOTSPOT_SCORE ERROR] Point {idx} Lat:{lat} Lon:{lon} Error:{e}")
                    # Continue with empty power_summary - scoring will use defaults
                
                # Extract parameters
                ndvi = float(pt.get("ndvi", 0.2))
                ndvi = max(0.0, min(1.0, ndvi))  # Clamp to 0-1
                
                population = int(pt.get("population", 2000))
                population = max(0, population)  # Ensure non-negative
                
                structure_type = pt.get("type", "generic")
                
                distance_to_roads_km = float(pt.get("road_km", 1.0))
                water_distance_km = float(pt.get("water_km", 2.0))
                
                # Compute score
                score = compute_score(
                    lat, lon, power_summary,
                    ndvi=ndvi,
                    population=population,
                    distance_to_roads_km=distance_to_roads_km,
                    water_distance_km=water_distance_km,
                    structure_type=structure_type
                )
                
                results.append({
                    "lat": lat,
                    "lon": lon,
                    "score": score,
                    "power_summary": power_summary,
                    "ndvi": ndvi,
                    "population": population,
                    "structure_type": structure_type
                })
                
            except (ValueError, TypeError) as e:
                errors.append(f"Point {idx}: Invalid data format - {str(e)}")
            except Exception as e:
                errors.append(f"Point {idx}: Unexpected error - {str(e)}")
                print(f"[HOTSPOT_SCORE UNEXPECTED] Point {idx}: {e}")

        response = {"results": results}
        if errors:
            response["warnings"] = errors
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[HOTSPOT_SCORE FATAL ERROR] {e}")
        return jsonify({"error": "Internal server error"}), 500

# --- Admin user creation ---
@app.route("/admin/create_user", methods=["POST"])
@login_required(role="admin")
def admin_create_user():
    """Create a new user (admin only)"""
    data = request.form
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "planner")
    
    if not username or not password:
        return "Username and password required", 400
    
    if len(password) < 6:
        return "Password must be at least 6 characters", 400
    
    if role not in ["admin", "planner"]:
        return "Invalid role. Must be 'admin' or 'planner'", 400
    
    try:
        create_user(username, generate_password_hash(password), role)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        print(f"[CREATE_USER ERROR] {e}")
        return "Failed to create user", 500
    
    return redirect(url_for("admin"))

@app.route("/api/users", methods=["GET"])
@login_required(role="admin")
def api_list_users():
    """List all users (admin only)"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, role FROM users ORDER BY username")
        users = [{"id": row[0], "username": row[1], "role": row[2]} for row in cursor.fetchall()]
        return jsonify({"users": users})
    except Exception as e:
        print(f"[LIST_USERS ERROR] {e}")
        return jsonify({"error": "Failed to fetch users"}), 500

@app.route("/api/user/<int:user_id>", methods=["DELETE"])
@login_required(role="admin")
def api_delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        # Prevent deleting yourself
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user[0] == session.get("user"):
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        print(f"[DELETE_USER ERROR] {e}")
        return jsonify({"error": "Failed to delete user"}), 500

# --- Health check ---
@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "time": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    })

# --- Error handlers ---
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template('500.html'), 500

# ----------------------
# --- Run App ----------
# ----------------------
if __name__ == "__main__":
    # Set session lifetime
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)
    app.run(debug=True, host="0.0.0.0", port=5000)