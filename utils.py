import sqlite3
import requests
import logging
from flask import g
from flask_caching import Cache
from config import Config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- Logging ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Cache ---------------- #
cache = Cache(config={
    "CACHE_TYPE": Config.CACHE_TYPE,
    "CACHE_DEFAULT_TIMEOUT": Config.CACHE_DEFAULT_TIMEOUT
})

# ---------------- Database ---------------- #
def get_db():
    """Get or create a SQLite database connection."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(Config.DATABASE)
        db.row_factory = sqlite3.Row
    return db


def query_user_by_username(username):
    """Fetch user details by username."""
    cur = get_db().cursor()
    cur.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def create_user(username, password_hash, role="planner"):
    """Create a new user in the database."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password_hash, role))
        db.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("User already exists")

# ---------------- NASA POWER API ---------------- #
def build_power_params(lat, lon, start, end, parameters="T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"):
    return {
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "format": "JSON",
        "community": "RE",
        "parameters": parameters
    }


def get_requests_session():
    """Return a requests.Session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=Config.RETRY_ATTEMPTS,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_power(lat, lon, start, end, parameters="T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"):
    """Fetch NASA POWER climate data."""
    base = Config.NASA_POWER_BASE
    params = build_power_params(lat, lon, start, end, parameters)
    session = get_requests_session()
    resp = session.get(base, params=params, timeout=Config.API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_power_data_and_summarize(lat, lon, start, end):
    """Fetch NASA POWER data, clean invalid values, and compute accurate means."""
    params_str = "T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"
    cache_key = f"power_data_{lat:.4f}_{lon:.4f}_{start}_{end}_{params_str}"

    data = cache.get(cache_key)
    if data is None:
        try:
            payload = build_power_params(lat, lon, start, end, parameters=params_str)
            logger.info(f"Fetching NASA POWER data for lat={lat}, lon={lon}, start={start}, end={end}")
            session = get_requests_session()
            resp = session.get(Config.NASA_POWER_BASE, params=payload, timeout=Config.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            if "properties" not in data or "parameter" not in data["properties"]:
                raise ValueError("Invalid NASA POWER response format")

            cache.set(cache_key, data, timeout=3600)
            logger.info(f"NASA POWER SUCCESS for {lat},{lon} - Data cached")

        except requests.exceptions.RequestException as e:
            logger.error(f"NASA POWER REQUEST FAILED for {lat},{lon}: {str(e)}")
            raise Exception(f"NASA POWER API error: {str(e)}")

    parameters = data["properties"]["parameter"]

    def clean_values(param_key):
        raw_values = list(parameters.get(param_key, {}).values())
        # Remove missing or invalid values (-999, None, "", etc.)
        valid = [float(v) for v in raw_values if v not in (None, "", -999, -999.0)]
        return valid

    # Clean data
    temp_values = clean_values("T2M")
    precip_values = clean_values("PRECTOTCORR")
    humidity_values = clean_values("RH2M")
    solar_values = clean_values("ALLSKY_SFC_SW_DWN")
    wind_values = clean_values("WS2M")

    # Compute means
    mean_temp = sum(temp_values) / len(temp_values) if temp_values else None
    mean_precip = sum(precip_values) if precip_values else None  # total precipitation (mm)
    mean_humidity = sum(humidity_values) / len(humidity_values) if humidity_values else None
    mean_solar = sum(solar_values) / len(solar_values) if solar_values else None
    mean_wind = sum(wind_values) / len(wind_values) if wind_values else None

    n_days = len(temp_values)

    logger.info(f"[NASA SUMMARY] Lat={lat}, Lon={lon} | Temp={mean_temp:.2f}°C | "
                f"Precip={mean_precip:.2f}mm | Days={n_days}")

    return {
        "mean_temp": round(mean_temp, 2) if mean_temp else None,
        "mean_precip": round(mean_precip, 2) if mean_precip else None,
        "mean_humidity": round(mean_humidity, 2) if mean_humidity else None,
        "mean_solar": round(mean_solar, 2) if mean_solar else None,
        "mean_wind": round(mean_wind, 2) if mean_wind else None,
        "n_days": n_days
    }

    def extract_mean(param_key):
        values = [float(v) for v in properties.get(param_key, {}).values() if v not in (None, "")]
        if not values:
            return None, 0
        return sum(values) / len(values), len(values)

    mean_temp, n_temp = extract_mean("T2M")
    mean_precip, _ = extract_mean("PRECTOTCORR")
    mean_humidity, _ = extract_mean("RH2M")
    mean_solar, _ = extract_mean("ALLSKY_SFC_SW_DWN")
    mean_wind, _ = extract_mean("WS2M")

    logger.info(f"Extracted NASA data for {lat},{lon}: Temp={mean_temp}, Precip={mean_precip}, Days={n_temp}")

    return {
        "mean_temp": mean_temp,
        "mean_precip": mean_precip,
        "mean_humidity": mean_humidity,
        "mean_solar": mean_solar,
        "mean_wind": mean_wind,
        "n_days": n_temp
    }

# ---------------- Scoring ---------------- #
def compute_score(lat, lon, power_summary=None, ndvi=None, population=None,
                  distance_to_roads_km=None, water_distance_km=None, structure_type="generic"):
    """Compute suitability score for a location."""

    ps = power_summary or {}
    mean_temp = ps.get("mean_temp")
    mean_precip = ps.get("mean_precip")

    using_defaults = []

    # --- Temperature ---
    if mean_temp is None:
        mean_temp = 25.0
        using_defaults.append("temperature")
    ideal_temp = 23.0
    temp_score = max(0.0, 100.0 - abs(mean_temp - ideal_temp) * 4.0)

    # --- Precipitation ---
    if mean_precip is None:
        mean_precip = 50.0  # fallback total rainfall in mm
        using_defaults.append("precipitation")

    # Convert total precipitation to approximate daily average
    if ps.get("n_days", 0) > 0:
        avg_precip = mean_precip / ps["n_days"]
    else:
        avg_precip = mean_precip

    # Score based on average daily rainfall
    if avg_precip < 50:
        precip_score = (avg_precip / 50.0) * 100.0
    elif avg_precip <= 150:
        precip_score = 100.0
    else:
        precip_score = max(0.0, 100.0 - (avg_precip - 150.0) * 0.5)

    precip_score = min(100.0, max(0.0, precip_score))


    # --- NDVI ---
    try:
        ndvi_val = float(ndvi) if ndvi is not None else 0.2
    except (ValueError, TypeError):
        ndvi_val = 0.2
    if ndvi is None:
        using_defaults.append("ndvi")
    ndvi_val = max(0.0, min(1.0, ndvi_val))
    ndvi_score = ndvi_val * 100.0

    # --- Population ---
    try:
        pop = int(population) if population is not None else 2000
    except (ValueError, TypeError):
        pop = 2000
    if population is None:
        using_defaults.append("population")

    if structure_type in ("hospital", "school"):
        pop_score = min(100.0, (pop / 10000.0) * 100.0)
    elif structure_type == "park":
        pop_score = (pop / 5000.0) * 100.0 if pop < 5000 else max(0.0, 100.0 - ((pop - 5000.0) / 5000.0) * 20.0)
    elif structure_type == "water":
        pop_score = min(100.0, (pop / 7000.0) * 80.0)
    else:
        pop_score = max(0.0, 100.0 - (pop / 10000.0) * 80.0)

    # --- Road Distance ---
    try:
        droad = float(distance_to_roads_km) if distance_to_roads_km is not None else 1.0
    except (ValueError, TypeError):
        droad = 1.0
    if distance_to_roads_km is None:
        using_defaults.append("road_distance")
    road_score = max(0.0, 100.0 - droad * 10.0)

    # --- Water Distance ---
    try:
        dw = float(water_distance_km) if water_distance_km is not None else 2.0
    except (ValueError, TypeError):
        dw = 2.0
    if water_distance_km is None:
        using_defaults.append("water_distance")

    if dw < 0.3:
        water_score = 0.0
    elif dw < 1.0:
        water_score = 50.0
    else:
        water_score = min(100.0, 50.0 + (dw - 1.0) * 10.0)

    # --- Weighting ---
    weights = {
        "hospital": {"temp": 0.25, "precip": 0.20, "ndvi": 0.10, "pop": 0.30, "road": 0.10, "water": 0.05},
        "school":   {"temp": 0.25, "precip": 0.15, "ndvi": 0.15, "pop": 0.25, "road": 0.15, "water": 0.05},
        "park":     {"temp": 0.20, "precip": 0.20, "ndvi": 0.35, "pop": 0.15, "road": 0.05, "water": 0.05},
        "water":    {"temp": 0.20, "precip": 0.25, "ndvi": 0.10, "pop": 0.15, "road": 0.15, "water": 0.15},
        "house":    {"temp": 0.30, "precip": 0.20, "ndvi": 0.20, "pop": 0.15, "road": 0.10, "water": 0.05},
        "generic":  {"temp": 0.28, "precip": 0.20, "ndvi": 0.18, "pop": 0.14, "road": 0.10, "water": 0.10}
    }

    w = weights.get(structure_type, weights["generic"])
    final_score = (
        w["temp"] * temp_score +
        w["precip"] * precip_score +
        w["ndvi"] * ndvi_score +
        w["pop"] * pop_score +
        w["road"] * road_score +
        w["water"] * water_score
    )
    final_score = max(0.0, min(100.0, final_score))

    logger.info(f"Score for {lat},{lon} ({structure_type}): {final_score:.2f}")
    if using_defaults:
        logger.warning(f"Using defaults for {lat},{lon}: {', '.join(using_defaults)}")

    return round(final_score, 2)


def score_location(*args, **kwargs):
    """Wrapper for compute_score (for external calls)."""
    return compute_score(*args, **kwargs)
