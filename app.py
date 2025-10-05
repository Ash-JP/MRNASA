import os
import math
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

# utils should provide DB helpers, cache and the POWER summarizer
from utils import get_db, query_user_by_username, create_user, cache, fetch_power_data_and_summarize, compute_score
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure a secret key exists
app.secret_key = app.config.get("SECRET_KEY", "change_me")

# Initialize cache (utils.cache expected to be a Flask-Caching instance)
cache.init_app(app)


# -------------------------
# Helpers
# -------------------------
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
    """Validate lat/lon and coerce to floats."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (ValueError, TypeError):
        return False, "Invalid coordinate format"
    if not (-90 <= lat_f <= 90):
        return False, "Latitude must be between -90 and 90"
    if not (-180 <= lon_f <= 180):
        return False, "Longitude must be between -180 and 180"
    return True, (lat_f, lon_f)


def haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in kilometers between two lat/lon points."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# -------------------------
# External data fetch helpers
# -------------------------
def fetch_ndvi(lat, lon, start, end):
    """
    Try MODIS RST API for NDVI subset. If fails, return fallback 0.2.
    Caches results using our cache object.
    """
    cache_key = f"ndvi_{lat:.6f}_{lon:.6f}_{start}_{end}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Default fallback
    ndvi_value = 0.2

    try:
        # ORNL MODIS RST API (common endpoint pattern). This may require adjustments in production.
        base = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
        params = {"latitude": lat, "longitude": lon, "startDate": start, "endDate": end}
        resp = requests.get(base, params=params, timeout=20)
        resp.raise_for_status()
        j = resp.json()
        subset = j.get("subset", [])
        vals = [float(item.get("value")) for item in subset if item.get("value") is not None]
        if vals:
            # MODIS NDVI in some datasets is scaled (e.g., -2000..10000). Try to normalize heuristically.
            mean_raw = sum(vals) / len(vals)
            # If values look like 0..10000 scale, convert to 0..1
            if mean_raw > 1.5:
                ndvi_value = max(0.0, min(1.0, mean_raw / 10000.0))
            else:
                ndvi_value = max(0.0, min(1.0, mean_raw))
    except Exception:
        # fallback left as 0.2
        pass

    cache.set(cache_key, ndvi_value, timeout=60 * 60)
    return ndvi_value


def fetch_population(lat, lon):
    """
    Attempt to fetch population density from a public service.
    If no reliable service is available or request fails, return fallback 2000.
    NOTE: Many population services require API keys or specific endpoints — adjust as needed.
    """
    cache_key = f"pop_{lat:.6f}_{lon:.6f}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    population = 2000
    # Try a WorldPop-like endpoint (placeholder pattern — may require adjustment)
    try:
        # This is a best-effort attempt; replace with your organization's preferred pop API if needed.
        wp_url = "https://api.worldpop.org/v1/population/point"
        params = {"latitude": lat, "longitude": lon, "year": 2020}
        resp = requests.get(wp_url, params=params, timeout=15)
        if resp.status_code == 200:
            j = resp.json()
            # Try different keys commonly used
            pop_val = None
            for k in ("population", "pop", "population_count", "value"):
                if k in j:
                    pop_val = j[k]
                    break
            if pop_val is not None:
                population = int(pop_val)
    except Exception:
        # fallback to SEDAC attempt
        try:
            sedac_url = "https://sedac.ciesin.columbia.edu/data/collection/gpw-v4"
            # Note: SEDAC often requires specific requests; we treat this as a placeholder.
            # If you have a SEDAC API/key, replace this logic with the proper endpoint.
            # leave fallback population = 2000
            pass
        except Exception:
            pass

    cache.set(cache_key, population, timeout=60 * 60 * 24)  # cache 1 day
    return population


def fetch_nearest_osm_distances(lat, lon, radius_m=2000):
    """
    Use Overpass API to find nearest highway/waterway and compute approximate distances (km).
    Returns (nearest_road_km, nearest_water_km).
    """
    cache_key = f"osm_{lat:.6f}_{lon:.6f}_{radius_m}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    overpass_url = "https://overpass-api.de/api/interpreter"
    nearest_road_km = None
    nearest_water_km = None

    # Find highways (ways and nodes). Use 'around' filter to get nearby features.
    try:
        query_highway = f"""
        [out:json][timeout:25];
        (
          node(around:{radius_m},{lat},{lon})[highway];
          way(around:{radius_m},{lat},{lon})[highway];
        );
        out center;
        """
        r = requests.post(overpass_url, data={"data": query_highway}, timeout=25)
        r.raise_for_status()
        elements = r.json().get("elements", [])
        for e in elements:
            # try to find a lat/lon for distance calc
            if "lat" in e and "lon" in e:
                e_lat = e["lat"]
                e_lon = e["lon"]
            elif "center" in e and isinstance(e["center"], dict):
                e_lat = e["center"].get("lat")
                e_lon = e["center"].get("lon")
            else:
                continue
            d = haversine_km(lat, lon, e_lat, e_lon)
            if nearest_road_km is None or d < nearest_road_km:
                nearest_road_km = d
    except Exception:
        nearest_road_km = None

    # Find waterways
    try:
        query_water = f"""
        [out:json][timeout:25];
        (
          node(around:{radius_m},{lat},{lon})[waterway];
          way(around:{radius_m},{lat},{lon})[waterway];
          relation(around:{radius_m},{lat},{lon})[waterway];
        );
        out center;
        """
        r2 = requests.post(overpass_url, data={"data": query_water}, timeout=25)
        r2.raise_for_status()
        elements = r2.json().get("elements", [])
        for e in elements:
            if "lat" in e and "lon" in e:
                e_lat = e["lat"]
                e_lon = e["lon"]
            elif "center" in e and isinstance(e["center"], dict):
                e_lat = e["center"].get("lat")
                e_lon = e["center"].get("lon")
            else:
                continue
            d = haversine_km(lat, lon, e_lat, e_lon)
            if nearest_water_km is None or d < nearest_water_km:
                nearest_water_km = d
    except Exception:
        nearest_water_km = None

    # Provide sensible defaults if not found
    if nearest_road_km is None:
        nearest_road_km = 5.0
    if nearest_water_km is None:
        nearest_water_km = 3.0

    cache.set(cache_key, (nearest_road_km, nearest_water_km), timeout=60 * 60)
    return nearest_road_km, nearest_water_km


# -------------------------
# Routes: UI pages
# -------------------------
@app.route("/")
def home():
    if "user" in session:
        # route based on role
        if session.get("role") == "admin":
            return redirect(url_for("admin"))
        return redirect(url_for("planner"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template("login_home.html", error="Username and password required")
        user = query_user_by_username(username)
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("planner"))
        return render_template("login_home.html", error="Invalid credentials")
    return render_template("login_home.html")

@app.route("/logout")
def logout():
    
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required(role="admin")
def admin():
    return render_template("admin.html", user=session.get("user"))


@app.route("/planner")
@login_required()
def planner():
    return render_template("planner.html", user=session.get("user"))


@app.route("/static/img/<path:filename>")
def static_img(filename):
    return send_from_directory(os.path.join(app.root_path, "static", "img"), filename)


# -------------------------
# API Endpoints
# -------------------------
@app.route("/api/power")
@login_required()
def api_power():
    """Proxy to NASA POWER (expects lat, lon, start, end)."""
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    start = request.args.get("start")
    end = request.args.get("end")
    if not (lat and lon):
        return jsonify({"error": "lat and lon required"}), 400

    ok, val = validate_coordinates(lat, lon)
    if not ok:
        return jsonify({"error": val}), 400
    lat_f, lon_f = val

    # default date window if missing
    if not start or not end:
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=30)
        start = start_dt.strftime("%Y%m%d")
        end = end_dt.strftime("%Y%m%d")

    try:
        data = fetch_power_data_and_summarize(lat_f, lon_f, start, end)
        return jsonify({"power_summary": data})
    except Exception as e:
        return jsonify({"error": "Failed to fetch POWER data", "details": str(e)}), 500


@app.route("/api/analyze_point", methods=["GET", "POST"])
@login_required()
def api_analyze_point():
    """
    Analyze a single point. Accepts JSON body (POST) with keys:
      lat, lon, start (YYYYMMDD), end (YYYYMMDD), ndvi (optional), population (optional), type (optional)
    Also supports GET query params: lat, lon, start, end.
    """
    # Accept both GET and POST
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
    else:
        body = request.args.to_dict()

    lat = body.get("lat")
    lon = body.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon required"}), 400

    ok, val = validate_coordinates(lat, lon)
    if not ok:
        return jsonify({"error": val}), 400
    lat_f, lon_f = val

    # dates
    start = body.get("start") or ""
    end = body.get("end") or ""
    if not start or not end:
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=30)
        start = start_dt.strftime("%Y%m%d")
        end = end_dt.strftime("%Y%m%d")

    # optional overrides
    ndvi_user = body.get("ndvi")
    population_user = body.get("population")
    structure_type = body.get("type", "generic")
    try:
        ndvi_user = float(ndvi_user) if ndvi_user is not None else None
    except (ValueError, TypeError):
        ndvi_user = None
    try:
        population_user = int(population_user) if population_user is not None else None
    except (ValueError, TypeError):
        population_user = None

    # 1) POWER summary (wrapped with cache inside utils)
    power_summary = {}
    try:
        power_summary = fetch_power_data_and_summarize(lat_f, lon_f, start, end)
    except Exception:
        # keep empty dict; compute_score will use defaults
        power_summary = {}

    # 2) NDVI
    ndvi_val = ndvi_user
    if ndvi_val is None:
        try:
            ndvi_val = fetch_ndvi(lat_f, lon_f, start, end)
        except Exception:
            ndvi_val = 0.2

    # 3) population
    pop_val = population_user if population_user is not None else fetch_population(lat_f, lon_f)

    # 4) OSM distances
    try:
        road_km, water_km = fetch_nearest_osm_distances(lat_f, lon_f, radius_m=3000)
    except Exception:
        road_km, water_km = (2.0, 2.0)

    # 5) score using imported compute_score from utils
    score = compute_score(
        lat_f, lon_f,
        power_summary=power_summary,
        ndvi=ndvi_val,
        population=pop_val,
        distance_to_roads_km=road_km,
        water_distance_km=water_km,
        structure_type=structure_type
    )

    return jsonify({
        "lat": lat_f,
        "lon": lon_f,
        "score": score,
        "power_summary": power_summary,
        "ndvi": ndvi_val,
        "population": pop_val,
        "road_km": road_km,
        "water_km": water_km,
        "structure_type": structure_type
    })


@app.route("/api/hotspot_score", methods=["POST"])
@login_required()
def api_hotspot_score():
    """
    Batch score multiple points. Accepts JSON:
      { "points": [ {lat, lon, type?, ndvi?, population?, road_km?, water_km?}, ... ], "start":..., "end":... }
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Invalid JSON payload"}), 400

    points = body.get("points", [])
    if not isinstance(points, list) or len(points) == 0:
        return jsonify({"error": "No points provided"}), 400
    if len(points) > 100:
        return jsonify({"error": "Max 100 points allowed per request"}), 400

    start = body.get("start", "")
    end = body.get("end", "")
    if not start or not end:
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=30)
        start = start_dt.strftime("%Y%m%d")
        end = end_dt.strftime("%Y%m%d")

    results = []
    for i, pt in enumerate(points):
        try:
            lat = pt.get("lat")
            lon = pt.get("lon")
            ok, val = validate_coordinates(lat, lon)
            if not ok:
                results.append({"error": f"Point {i} invalid coordinates: {val}"})
                continue
            lat_f, lon_f = val

            # optional overrides
            ndvi_user = pt.get("ndvi")
            pop_user = pt.get("population")
            struct_type = pt.get("type", "generic")
            road_km = pt.get("road_km")
            water_km = pt.get("water_km")

            if ndvi_user is not None:
                try:
                    ndvi_user = float(ndvi_user)
                except (ValueError, TypeError):
                    ndvi_user = None
            if pop_user is not None:
                try:
                    pop_user = int(pop_user)
                except (ValueError, TypeError):
                    pop_user = None

            # fetch POWER
            power_summary = {}
            try:
                power_summary = fetch_power_data_and_summarize(lat_f, lon_f, start, end)
            except Exception:
                power_summary = {}

            # NDVI/pop/OSM distances
            ndvi_val = ndvi_user if ndvi_user is not None else fetch_ndvi(lat_f, lon_f, start, end)
            pop_val = pop_user if pop_user is not None else fetch_population(lat_f, lon_f)

            if road_km is None or water_km is None:
                r_km, w_km = fetch_nearest_osm_distances(lat_f, lon_f, radius_m=3000)
                road_km = road_km if road_km is not None else r_km
                water_km = water_km if water_km is not None else w_km

            score = compute_score(
                lat_f, lon_f,
                power_summary=power_summary,
                ndvi=ndvi_val,
                population=pop_val,
                distance_to_roads_km=road_km,
                water_distance_km=water_km,
                structure_type=struct_type
            )

            results.append({
                "lat": lat_f,
                "lon": lon_f,
                "score": score,
                "power_summary": power_summary,
                "ndvi": ndvi_val,
                "population": pop_val,
                "road_km": road_km,
                "water_km": water_km,
                "structure_type": struct_type
            })
        except Exception as e:
            results.append({"error": f"Point {i} processing error: {str(e)}"})

    return jsonify({"results": results})


# -------------------------
# Admin helper endpoints
# -------------------------
@app.route("/admin/create_user", methods=["POST"])
@login_required(role="admin")
def admin_create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "planner")
    if not username or not password:
        return "Username and password required", 400
    if role not in ("admin", "planner"):
        return "Invalid role", 400
    try:
        create_user(username, generate_password_hash(password), role)
    except ValueError as e:
        return str(e), 400
    return redirect(url_for("admin"))


@app.route("/api/users", methods=["GET"])
@login_required(role="admin")
def api_list_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, role FROM users ORDER BY username")
    users = [{"id": r["id"], "username": r["username"], "role": r["role"]} for r in cur.fetchall()]
    return jsonify({"users": users})


@app.route("/api/user/<int:user_id>", methods=["DELETE"])
@login_required(role="admin")
def api_delete_user(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "User not found"}), 404
    if row["username"] == session.get("user"):
        return jsonify({"error": "Cannot delete your own account"}), 400
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({"message": "User deleted"})


# -------------------------
# Health & error handlers
# -------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.datetime.utcnow().isoformat() + "Z"})


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("500.html"), 500


# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    # session lifetime (adjust as desired)
    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=24)
    app.run(debug=True, host="0.0.0.0", port=5000)