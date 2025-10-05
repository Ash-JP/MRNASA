import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Base configuration - shared across all environments."""

    # --- Application & Security ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable not set!")

    # --- Database & Caching ---
    DATABASE = os.path.join(BASE_DIR, "app.db")
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 3600))

    # --- API Settings ---
    NASA_POWER_BASE = os.environ.get(
        "NASA_POWER_BASE", "https://power.larc.nasa.gov/api/temporal/daily/point"
    )
    OVERPASS_API_BASE = os.environ.get(
        "OVERPASS_API_BASE", "https://overpass-api.de/api/interpreter"
    )
    GIBS_WMTS = os.environ.get(
        "GIBS_WMTS",
        "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{layer}/default/{time}/{tilematrixset}/{z}/{y}/{x}.jpg"
    )
    SEDAC_API_BASE = os.environ.get(
        "SEDAC_API_BASE", "https://sedac.ciesin.columbia.edu"
    )
    CMR_BASE = os.environ.get(
        "CMR_BASE", "https://cmr.earthdata.nasa.gov/search"
    )

    # --- Request Handling ---
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", 30))   # seconds
    RETRY_ATTEMPTS = int(os.environ.get("RETRY_ATTEMPTS", 3))

    # --- General ---
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "RedisCache")
    CACHE_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class TestingConfig(Config):
    TESTING = True
    DATABASE = os.path.join(BASE_DIR, "test.db")
