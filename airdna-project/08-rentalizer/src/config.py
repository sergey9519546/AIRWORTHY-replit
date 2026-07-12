"""Configuration settings."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings:
    MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
    REALIE_API_KEY = os.getenv("REALIE_API_KEY", "")
    REALIE_BASE_URL = "https://app.realie.ai/api"
    REALIE_TIMEOUT = 6  # seconds — parcel enrichment must never stall the estimate
    MODEL_PATH = os.path.join(BASE_DIR, "models", "revenue_model.pkl")
    META_PATH = os.path.join(BASE_DIR, "models", "meta.json")
    FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")
    TRAIN_DATA_PATH = os.path.join(BASE_DIR, "data", "train.csv")

    CACHE_TTL = int(os.getenv("CACHE_TTL", "604800"))  # 7 days
    CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "10000"))

    NYC_LAT_MIN, NYC_LAT_MAX = 40.49, 40.92
    NYC_LNG_MIN, NYC_LNG_MAX = -74.26, -73.70

    NIGHTLY_RATE_MIN = 25.0
    NIGHTLY_RATE_MAX = 5000.0
    MAX_COMPS = 20
    MAX_BATCH = 20

    VERSION = "1.0.0"
    DATA_FRESHNESS = "2026-06-14"

    DISCLAIMER = (
        "Revenue estimates are provided for informational purposes only and do not constitute "
        "financial, investment, or real estate advice. Estimates are based on historical data from "
        "InsideAirbnb and may not reflect current market conditions. Actual revenue may vary "
        "significantly from estimates. This tool makes no guarantees of accuracy and shall not be "
        "liable for any decisions made based on these estimates. Consult a qualified professional "
        "before making investment decisions."
    )

    DATA_SOURCE = "InsideAirbnb (insideairbnb.com) — CC BY 4.0"
    LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

settings = Settings()
