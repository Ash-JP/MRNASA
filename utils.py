import sqlite3
from config import Config
from flask import g
import requests
from flask_caching import Cache

# Initialize cache
cache = Cache(config={
    'CACHE_TYPE': Config.CACHE_TYPE,
    'CACHE_DEFAULT_TIMEOUT': Config.CACHE_DEFAULT_TIMEOUT
})

# ---------------------------
# --- Database Helpers ------
# ---------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(Config.DATABASE)
        db.row_factory = sqlite3.Row
    return db

def query_user_by_username(username):
    cur = get_db().cursor()
    cur.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
    return cur.fetchone()

def create_user(username, password_hash, role="planner"):
    cur = get_db().cursor()
    try:
        cur.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", (username, password_hash, role))
        get_db().commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("User already exists")

# ---------------------------
# --- NASA POWER API --------
# ---------------------------
def build_power_params(lat, lon, start, end, parameters="T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"):
    """
    Build request payload for NASA POWER API.
    Default parameters include temperature, precipitation, humidity, solar radiation, wind.
    """
    return {
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "format": "JSON",
        "community": "RE",
        "parameters": parameters
    }

def fetch_power(lat, lon, start, end, parameters="T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"):
    """
    Fetch raw daily POWER data for a coordinate.
    Used mainly by /api/power endpoint.
    """
    base = Config.NASA_POWER_BASE
    params = build_power_params(lat, lon, start, end, parameters)
    resp = requests.get(base, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def fetch_power_data_and_summarize(lat, lon, start, end):
    """
    Fetches NASA POWER data (temp, precipitation, humidity, solar radiation, wind),
    utilizes cache, and calculates averages.
    Used by /api/hotspot_score endpoint.
    """
    power_base_url = Config.NASA_POWER_BASE
    params_str = "T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M"
    cache_key = f"power_score_data_{lat}_{lon}_{start}_{end}_{params_str}"
    
    data = cache.get(cache_key)
    if data is None:
        payload = build_power_params(lat, lon, start, end, parameters=params_str)
        resp = requests.get(power_base_url, params=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, timeout=3600)  # cache for 1 hour

    properties = data.get("properties", {}).get("parameter", {})

    def extract_mean(param_key):
        data_series = properties.get(param_key, {})
        values = [float(v) for v in data_series.values() if v not in (None, '', "null")]
        return (sum(values) / len(values)) if values else None, len(values)

    mean_temp, n_temp = extract_mean("T2M")
    mean_precip, n_precip = extract_mean("PRECTOTCORR")
    mean_humidity, _ = extract_mean("RH2M")
    mean_solar, _ = extract_mean("ALLSKY_SFC_SW_DWN")
    mean_wind, _ = extract_mean("WS2M")

    return {
        "mean_temp": mean_temp,
        "mean_precip": mean_precip,
        "mean_humidity": mean_humidity,
        "mean_solar": mean_solar,
        "mean_wind": mean_wind,
        "n_days": n_temp
    }

# ---------------------------
# --- (Deprecated) Scoring --
# ---------------------------
def score_location(*args, **kwargs):
    """
    Deprecated: scoring now handled in app.py:compute_score
    This is left here only for backward compatibility.
    """
    return 0
