import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DATABASE = os.path.join(BASE_DIR, "app.db")
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour default, tune per endpoint
    NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
    GIBS_WMTS = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{layer}/default/{time}/{tilematrixset}/{z}/{y}/{x}.jpg"
    SEDAC_BASE = "https://sedac.ciesin.columbia.edu"
    CMR_BASE = "https://cmr.earthdata.nasa.gov/search"