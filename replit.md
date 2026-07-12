:# Airbnb Analysis & Rentalizer

Airbnb data analysis project with three connected parts: a revenue estimator, a data analysis pipeline, and a map explorer.

## 1. Rentalizer Web App (`airdna-project/08-rentalizer/`)

A FastAPI web app with a pre-trained ML model (XGBoost + LightGBM) that estimates annual short-term rental revenue for any NYC address.

**Run command:**
```bash
cd airdna-project/08-rentalizer && \
  LD_LIBRARY_PATH=/nix/store/bmi5znnqk4kg2grkrhk6py0irc8phf6l-gcc-14.2.1.20250322-lib/lib:$LD_LIBRARY_PATH \
  uvicorn src.api:app --host 0.0.0.0 --port 5000
```

**Pages:**
- `/` — Revenue estimator for NYC addresses
- `/map` — Interactive map explorer for California & Florida listings

**API endpoints:**
- `POST /v1/estimate` — Revenue estimate for one property
- `GET /api/listings` — Listings inside a map bounding box (supports state, city, room_type, price filters)
- `GET /api/cities` — Cities available in the loaded data

**Key files:**
- `src/api.py` — FastAPI routes
- `src/model.py` — ML model loading/prediction
- `src/comp_finder.py` — comparable-listing search
- `templates/map.html` & `static/map.js` — map frontend
- `models/revenue_model.pkl` — pre-trained model
- `data/train.csv` — training data used to build comp index

**Optional env vars:**
- `MAPBOX_TOKEN` — if set, uses Mapbox for geocoding; otherwise falls back to free Nominatim
- `API_KEYS` — comma-separated API keys to enable auth (dev mode: no auth)

## 2. Map Explorer (`/map`)

A Leaflet + MarkerCluster map showing Airbnb listings across California and Florida, loaded from InsideAirbnb snapshots. Filters include state, city/region, room type, and min/max price. Click a marker for listing details (price, estimated revenue, reviews).

**Current data loaded (latest snapshot per city):**
- California: Los Angeles, Oakland, Pacific Grove, San Diego, San Francisco, San Mateo County, Santa Clara County, Santa Cruz County
- Florida: Broward County

## 3. Data Analysis Pipeline (`airdna-project/`)

Jupyter notebooks + SQLite for multi-tier Airbnb market analysis.

**Setup:**
```bash
# Create database (run once)
cd airdna-project && python scripts/create_database.py

# Load latest listings for the map (fast)
python scripts/load_map_data.py

# Load all raw data CSVs (slow, includes calendar + reviews)
python scripts/load_data.py

# Validate data
python scripts/validate_data.py

# Start Jupyter
jupyter notebook notebooks/
```

**Data source:** [InsideAirbnb](https://insideairbnb.com/get-the-data/) — regional snapshots
Raw CSVs are downloaded automatically by the load scripts into `airdna-project/data/raw/<state>/<city>/<date>/`.

**Database:** `airdna-project/db/airbnb.db` (SQLite, auto-created by setup script)

## Analysis Tiers

| Tier | Topic | Days |
|------|-------|------|
| 0 | Data Audit | 1–3 |
| 1 | Market Overview (borough, room type, revenue) | 4–8 |
| 2 | Location Scoring (ghost listings, host concentration, seasonality) | 9–14 |
| 3 | Deep Analysis (price prediction, amenity impact, dashboard) | 15–28 |

## User Preferences
