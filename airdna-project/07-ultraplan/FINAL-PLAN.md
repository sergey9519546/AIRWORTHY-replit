# ULTRAPLAN v3 — Complete Step-by-Step Build Plan

> Every task. Every file. Every line that matters. From zero to deployed.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                    FRONTEND                      │
│  Single HTML page + vanilla JS + Mapbox GL       │
│  Input form → fetch API → render results         │
│  Revenue range card, comps list, map pins        │
└──────────────────┬──────────────────────────────┘
                   │ POST /v1/estimate
                   ▼
┌─────────────────────────────────────────────────┐
│                    BACKEND                       │
│  FastAPI + uvicorn                               │
│  ┌─────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │Validate │→│Geocode   │→│Find Comps         │ │
│  │Input    ││Mapbox+Nom ││KD-Tree + Filter    │ │
│  └─────────┘ └──────────┘ └───────────────────┘ │
│  ┌──────────────────┐ ┌──────────────────────┐  │
│  │Feature Engineer   │→│Predict (XGBoost)     │  │
│  │comp stats + dist  ││+ blend with comp avg  │  │
│  └──────────────────┘ └──────────────────────┘  │
│  ┌──────────────────┐ ┌──────────────────────┐  │
│  │Confidence CI      │→│Format + Disclaimers  │  │
│  │percentile-based   ││CC BY 4.0 attribution  │  │
│  └──────────────────┘ └──────────────────────┘  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│                    DATA                          │
│  InsideAirbnb NYC (30,259 listings)              │
│  XGBoost model (revenue_model.pkl)               │
│  KD-Tree index (in-memory, 5K listings)          │
│  Geocode cache (TTLCache, 7 days)                │
└─────────────────────────────────────────────────┘
```

---

## File Structure

```
airdna-project/08-rentalizer/
├── src/
│   ├── __init__.py
│   ├── config.py                 # All settings, paths, constants
│   ├── schemas.py                # Pydantic request/response models
│   ├── exceptions.py             # Custom exceptions + FastAPI handlers
│   ├── validation.py             # Input validation + NYC bounds
│   ├── geocoder.py               # Mapbox primary, Nominatim fallback, cache
│   ├── comp_finder.py            # KD-Tree comp search + scoring
│   ├── features.py               # Feature engineering pipeline
│   ├── model.py                  # Model loading, prediction, blend
│   ├── confidence.py             # CI computation from comp variance
│   └── api.py                    # FastAPI app, routes, middleware
├── scripts/
│   ├── prepare_data.py           # Data cleaning + feature engineering
│   ├── train_model.py            # Optuna tuning + training + evaluation
│   └── build_index.py            # Build KD-Tree index from training data
├── templates/
│   └── index.html                # Single-page web app
├── static/
│   ├── style.css
│   └── app.js
├── tests/
│   ├── conftest.py               # Shared fixtures + mocks
│   ├── unit/
│   │   ├── test_geocoder.py      # 15 tests
│   │   ├── test_comp_finder.py   # 20 tests
│   │   ├── test_features.py      # 15 tests
│   │   ├── test_model.py         # 10 tests
│   │   ├── test_confidence.py    # 8 tests
│   │   └── test_validation.py    # 12 tests
│   ├── integration/
│   │   ├── test_api_e2e.py       # 15 tests
│   │   └── test_pipeline.py      # 8 tests
│   └── edge_cases/
│       └── test_boundaries.py    # 20 tests
├── data/
│   ├── train.csv                 # 80% of cleaned data
│   ├── test.csv                  # 20% holdout
│   └── geocode_cache.json        # Persisted geocode cache
├── models/
│   ├── revenue_model.pkl         # Trained XGBoost model
│   ├── feature_importance.json   # SHAP values
│   └── meta.json                 # Model version, training date, metrics
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md                     # With CC BY 4.0 attribution
```

---

## Phase 1: Data Preparation

### Task 1.1: Load and Clean Data
**File:** `scripts/prepare_data.py`
**Input:** `airdna-project/06-insideairbnb-data/listings.csv.gz`
**Output:** `data/train.csv`, `data/test.csv`

Steps:
1. Load CSV with `pandas.read_csv(low_memory=False)`
2. Filter: `room_type == 'Entire home/apt'`
3. Filter: `has_availability == 't'`
4. Filter: `minimum_nights <= 30`
5. Parse `price` column: strip `$`, `,`, convert to float
6. Parse `estimated_revenue_l365d` to numeric
7. Drop rows where `estimated_revenue_l365d <= 0` or `price_num <= 0`
8. Drop rows where `estimated_revenue_l365d` is NaN
9. Remove outliers: keep only listings with revenue between 1st and 99th percentile
10. Result: ~5,000 labeled STR listings

### Task 1.2: Feature Engineering
**Same file:** `scripts/prepare_data.py`

Create these features:

**Numeric:**
- `price_num` — nightly rate (cleaned)
- `accommodates` — guest capacity
- `bedrooms` — fill NaN with 0 (studio)
- `bathrooms` — parse from `bathrooms_text`, fill NaN with 1
- `beds` — fill NaN with accommodates/2
- `minimum_nights` — as numeric
- `number_of_reviews` — total reviews
- `number_of_reviews_ltm` — reviews last 12 months
- `reviews_per_month` — fill NaN with 0
- `availability_30`, `availability_60`, `availability_90`, `availability_365`
- `review_scores_rating` — fill NaN with median
- `host_listings_count` — fill NaN with 1
- `latitude`, `longitude`

**Derived:**
- `review_recency_days` — days since `last_review` (fillna with 9999)
- `host_experience_months` — months since `host_since`
- `listing_age_months` — months since `first_review`
- `price_per_person` — `price_num / accommodates`
- `reviews_ltm_ratio` — `number_of_reviews_ltm / max(number_of_reviews, 1)`
- `occupancy_proxy` — `(365 - availability_365) / 365`

**Categorical (one-hot encode):**
- `neighbourhood_group_cleansed` — borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- `property_type` — group rare types (<20 listings) into "Other"
- `instant_bookable` — t/f → 1/0
- `host_is_superhost` — t/f → 1/0

**Target:**
- `log_revenue` — `np.log1p(estimated_revenue_l365d)` (log-transform for training)

### Task 1.3: Train/Test Split
**Same file:** `scripts/prepare_data.py`

1. Create revenue tier: `pd.qcut(estimated_revenue_l365d, 5, labels=False)`
2. Create stratification key: `borough + '_' + str(revenue_tier)`
3. `train_test_split(test_size=0.2, stratify=stratification_key, random_state=42)`
4. Save `data/train.csv` and `data/test.csv`
5. Print summary stats for both sets

### Task 1.4: Verify Data Quality
**Same file:** `scripts/prepare_data.py`

Checks:
- No NaN in any feature column
- No infinite values
- Revenue > 0 for all rows
- Price > 0 for all rows
- Latitude between 40.49 and 40.92 (NYC bounds)
- Longitude between -74.26 and -73.70
- Train set has >3,000 rows
- Test set has >500 rows
- All 5 boroughs represented in both sets

---

## Phase 2: Model Training

### Task 2.1: Baseline Models
**File:** `scripts/train_model.py`

Baseline 1: Median by (borough, bedrooms)
```python
# For each (borough, bedrooms) combo, predict median revenue
# Measure MAPE, MAE, R² on test set
```

Baseline 2: Ridge Regression
```python
# Train Ridge on all features
# Measure MAPE, MAE, R² on test set
```

Baseline 3: k-NN Comp-Based
```python
# For each test listing, find 10 nearest training listings
# Predict = weighted average of comp revenues
# Measure MAPE, MAE, R² on test set
```

### Task 2.2: Optuna Hyperparameter Tuning
**Same file:** `scripts/train_model.py`

```python
import optuna

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 8),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
    }
    # 5-fold CV, return mean MAPE
    ...

study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=50)
```

### Task 2.3: Train Final XGBoost Model
**Same file:** `scripts/train_model.py`

1. Use best params from Optuna
2. Train on full training set with early stopping (20% of train as validation)
3. Evaluate on test set: MAPE, MdAPE, R², MAE, Within 25%, Within 50%
4. Apply Duan's smearing correction for log-transform bias:
   ```python
   smearing_factor = np.mean(np.exp(residuals))
   predictions = np.expm1(log_predictions) * smearing_factor
   ```

### Task 2.4: Train LightGBM + CatBoost (Baselines)
**Same file:** `scripts/train_model.py`

1. Train LightGBM with same features (default params)
2. Train CatBoost with same features (default params)
3. Compare all three on test set
4. Pick best model (lowest MAPE)

### Task 2.5: Optimize Blend Weight
**Same file:** `scripts/train_model.py`

```python
# Grid search alpha in [0, 0.1, ..., 1.0]
# For each alpha:
#   final = alpha * xgb_pred + (1-alpha) * comp_pred
#   measure MAPE on test set
# Pick alpha with lowest MAPE
# Also try Ridge meta-learner on (xgb_pred, comp_pred)
```

### Task 2.6: Feature Importance + Validation
**Same file:** `scripts/train_model.py`

1. Compute SHAP values for all features
2. Plot top 15 features (save as PNG)
3. Check: price should NOT be the dominant feature (leakage check)
4. Check: revenue increases monotonically with price (sanity)
5. Check: more bedrooms → higher revenue (sanity)
6. Save `models/feature_importance.json`

### Task 2.7: Stratified Evaluation
**Same file:** `scripts/train_model.py`

Report metrics separately for:
- Each borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- Each revenue tier (<$15K, $15-30K, $30-60K, $60-100K, >$100K)
- Overall

### Task 2.8: Save Model + Metadata
**Same file:** `scripts/train_model.py`

1. Save model: `joblib.dump(model, 'models/revenue_model.pkl')`
2. Save metadata:
   ```json
   {
     "model_type": "xgboost",
     "version": "1.0.0",
     "trained_at": "2026-06-29T06:00:00Z",
     "n_train": 4000,
     "n_test": 1000,
     "features": [...],
     "metrics": {"mape": 0.35, "r2": 0.75, ...},
     "optuna_params": {...},
     "blend_alpha": 0.6,
     "smearing_factor": 1.05
   }
   ```

---

## Phase 3: Comparable Finder

### Task 3.1: Build KD-Tree Index
**File:** `scripts/build_index.py`

1. Load training data
2. Extract lat/lng columns
3. Build `scipy.spatial.KDTree` on lat/lng (radians for haversine)
4. Save index (pickle or rebuild on startup)
5. Store training data in memory for comp lookup

### Task 3.2: Comp Finder Module
**File:** `src/comp_finder.py`

```python
def find_comps(lat, lng, bedrooms, accommodates, room_type, k=20):
    # 1. Query KD-Tree for k=20 nearest
    # 2. Filter: room_type match
    # 3. Filter: bedrooms within ±1
    # 4. Filter: accommodates within ±2
    # 5. If <3 comps after filter, relax filters
    # 6. If 0 comps, return empty with warning
    # 7. Score each comp:
    #    distance_score = max(0, 1 - distance_km / 10) * 0.40
    #    bedroom_score = (1 - abs(diff) / max(target, 1)) * 0.25
    #    bath_score = (1 - abs(diff) / max(target, 1)) * 0.15
    #    capacity_score = (1 - abs(diff) / max(target, 1)) * 0.15
    #    type_score = (1.0 if match else 0.3) * 0.05
    #    total = sum of all scores
    # 8. Return sorted by score descending
```

### Task 3.3: Comp-Based Prediction
**Same file:** `src/comp_finder.py`

```python
def predict_from_comps(comps):
    if len(comps) == 0:
        return None, "no_comps"
    weights = [c.score for c in comps]
    revenues = [c.revenue for c in comps]
    weighted_avg = np.average(revenues, weights=weights)
    cv = np.std(revenues) / np.mean(revenues) if np.mean(revenues) > 0 else 1.0
    return weighted_avg, cv
```

---

## Phase 4: Geocoding

### Task 4.1: Geocoder Module
**File:** `src/geocoder.py`

```python
from geopy.geocoders import MapBox, Nominatim
from cachetools import TTLCache

cache = TTLCache(maxsize=10000, ttl=7*24*3600)  # 7 days

def geocode(address):
    # 1. Normalize address (lowercase, strip whitespace)
    # 2. Check cache
    # 3. Try Mapbox first (if MAPBOX_TOKEN set)
    # 4. Fallback to Nominatim
    # 5. Validate NYC bounds (40.49-40.92 lat, -74.26 to -73.70 lng)
    # 6. Return GeocodeResult(lat, lng, display_name, source)
    # 7. Raise GeocodingError if failed
```

### Task 4.2: NYC Bounds Validation
**File:** `src/validation.py`

```python
NYC_BOUNDS = {
    "lat_min": 40.49, "lat_max": 40.92,
    "lng_min": -74.26, "lng_max": -73.70,
}

def is_in_nyc(lat, lng):
    return (NYC_BOUNDS["lat_min"] <= lat <= NYC_BOUNDS["lat_max"] and
            NYC_BOUNDS["lng_min"] <= lng <= NYC_BOUNDS["lng_max"])
```

---

## Phase 5: Feature Engineering for Inference

### Task 5.1: Feature Pipeline
**File:** `src/features.py`

```python
def build_features(listing_data, comps, geocode_result):
    """Build feature vector for a single prediction."""
    features = {}
    
    # From user input
    features['price_num'] = listing_data.nightly_rate
    features['accommodates'] = listing_data.accommodates
    features['bedrooms'] = listing_data.bedrooms
    features['bathrooms'] = listing_data.bathrooms
    features['latitude'] = geocode_result.lat
    features['longitude'] = geocode_result.lng
    
    # From comps (aggregated)
    features['comp_median_price'] = np.median([c.price for c in comps])
    features['comp_median_revenue'] = np.median([c.revenue for c in comps])
    features['comp_count'] = len(comps)
    features['avg_comp_distance_km'] = np.mean([c.distance_km for c in comps])
    
    # From market data
    features['borough_encoded'] = get_borough(geocode_result.lat, geocode_result.lng)
    
    # One-hot encode categoricals
    # ...
    
    return features
```

---

## Phase 6: API Backend

### Task 6.1: Configuration
**File:** `src/config.py`

```python
class Settings:
    MAPBOX_TOKEN: str = os.getenv("MAPBOX_TOKEN", "")
    MODEL_PATH: str = "models/revenue_model.pkl"
    DATA_PATH: str = "data/train.csv"
    CACHE_TTL: int = 7 * 24 * 3600  # 7 days
    CACHE_MAXSIZE: int = 10000
    NYC_LAT_RANGE: tuple = (40.49, 40.92)
    NYC_LNG_RANGE: tuple = (-74.26, -73.70)
    NIGHTLY_RATE_MIN: float = 25.0
    NIGHTLY_RATE_MAX: float = 5000.0
    MAX_COMPS: int = 20
    VERSION: str = "1.0.0"
```

### Task 6.2: Pydantic Schemas
**File:** `src/schemas.py`

```python
class EstimateRequest(BaseModel):
    address: str
    bedrooms: int = Field(ge=0, le=10)
    bathrooms: int = Field(ge=0, le=10)
    accommodates: int = Field(ge=1, le=20)
    nightly_rate: float = Field(gt=0, le=10000)
    property_type: str = "Entire home/apt"

class ConfidenceResponse(BaseModel):
    level: str  # "high", "medium", "low"
    revenue_lower: float
    revenue_upper: float
    cv: float

class CompResponse(BaseModel):
    distance_km: float
    bedrooms: int
    revenue: float
    similarity_score: float
    borough: str

class EstimateResponse(BaseModel):
    address: str
    lat: float
    lng: float
    annual_revenue: float
    confidence: ConfidenceResponse
    comps: list[CompResponse]
    market: dict
    disclaimer: str
    data_source: str
    model_version: str

class ErrorResponse(BaseModel):
    error: str
    detail: str
    suggestion: str = ""
```

### Task 6.3: Custom Exceptions
**File:** `src/exceptions.py`

```python
class GeocodingError(Exception): ...
class OutsideCoverageError(Exception): ...
class InsufficientCompsError(Exception): ...
class ModelNotReadyError(Exception): ...
class InvalidInputError(Exception): ...
```

### Task 6.4: FastAPI Application
**File:** `src/api.py`

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Rentalizer", version="1.0.0")

# Startup: load model, build KD-Tree index, load training data
@app.on_event("startup")
def startup():
    load_model()
    load_index()
    load_market_stats()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the web UI."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/v1/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest):
    """Single property revenue estimate."""
    # 1. Validate input
    # 2. Geocode address
    # 3. NYC bounds check
    # 4. Find comps
    # 5. Build features
    # 6. Predict (XGBoost)
    # 7. Predict (comp-based)
    # 8. Blend
    # 9. Compute confidence
    # 10. Format response with disclaimers

@app.post("/v1/batch", response_model=list[EstimateResponse])
async def batch_estimate(requests: list[EstimateRequest]):
    """Batch estimates (max 20)."""
    # Validate batch size
    # Process each with error isolation
    # Return array (errors as ErrorResponse in slot)

@app.get("/v1/health")
async def health():
    return {"status": "ok"}

@app.get("/v1/ready")
async def ready():
    return {"model_loaded": model_loaded, "index_loaded": index_loaded}

@app.get("/v1/model/info")
async def model_info():
    return model_metadata

@app.get("/v1/credits")
async def credits():
    return {
        "data_source": "InsideAirbnb",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Data from InsideAirbnb (insideairbnb.com), licensed under CC BY 4.0"
    }

# Exception handlers
@app.exception_handler(GeocodingError)
async def geocoding_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": "geocoding_failed", ...})

@app.exception_handler(OutsideCoverageError)
async def coverage_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": "outside_coverage_area", ...})
```

### Task 6.5: Response Formatting
**Same file:** `src/api.py`

Every response includes:
```python
{
    "disclaimer": "Revenue estimates are for informational purposes only and do not constitute financial advice. Actual revenue may vary significantly. Consult a qualified professional before making investment decisions.",
    "data_source": "InsideAirbnb (insideairbnb.com) — CC BY 4.0",
    "model_version": "1.0.0",
    "data_freshness": "2026-06-14"
}
```

---

## Phase 7: Frontend

### Task 7.1: HTML Template
**File:** `templates/index.html`

Single page with:
- Header with title and attribution
- Input form: address (autocomplete), bedrooms, bathrooms, accommodates, nightly_rate, property_type
- Submit button
- Results card (hidden until response):
  - Revenue range (big number, lower-upper)
  - Confidence badge (green/yellow/red)
  - Monthly breakdown (12 bars)
  - Comps list (top 5 with distance and revenue)
  - Map with pins (Mapbox GL JS)
  - Market stats sidebar
- Footer with disclaimers and CC BY 4.0 attribution

### Task 7.2: CSS
**File:** `static/style.css`

Clean, modern design:
- Mobile-first responsive
- Revenue number: large, bold
- Confidence: color-coded badge
- Comps: card layout
- Map: full-width, 400px height
- Disclaimers: muted text, always visible

### Task 7.3: JavaScript
**File:** `static/app.js`

```javascript
// 1. Form submission handler
// 2. POST to /v1/estimate with JSON body
// 3. Handle errors (422, 500)
// 4. Render results:
//    - Revenue range text
//    - Confidence badge
//    - Monthly chart (12 bars, CSS-only)
//    - Comps list
//    - Map pins (Mapbox GL JS)
// 5. Loading spinner during request
// 6. Input validation (client-side)
```

---

## Phase 8: Testing

### Task 8.1: Test Fixtures
**File:** `tests/conftest.py`

```python
@pytest.fixture
def valid_request():
    return {"address": "350 5th Ave, New York, NY", "bedrooms": 2, ...}

@pytest.fixture
def mock_geocoder():
    # Return fixed lat/lng for known addresses

@pytest.fixture
def mock_model():
    # Return fixed predictions

@pytest.fixture
def client():
    # FastAPI TestClient
```

### Task 8.2: Unit Tests (80 tests)
**Files:** `tests/unit/test_*.py`

**test_geocoder.py (15 tests):**
- Valid NYC address returns lat/lng
- Address cached on second call
- Non-NYC address raises OutsideCoverageError
- Empty address raises InvalidInputError
- Nominatim fallback works
- Cache TTL expires

**test_comp_finder.py (20 tests):**
- Finds comps in Manhattan
- Returns empty for remote area
- Score decreases with distance
- Bedroom match scores higher than mismatch
- Filters by room_type
- Handles 0 comps gracefully

**test_features.py (15 tests):**
- Builds correct feature vector
- Handles missing bedrooms (studio)
- Handles missing bathrooms
- One-hot encodes borough correctly
- Price per person computed correctly

**test_model.py (10 tests):**
- Model loads successfully
- Prediction is positive
- Prediction < price × 365
- Higher price → higher prediction
- More bedrooms → higher prediction

**test_confidence.py (8 tests):**
- Contains prediction within bounds
- Lower bound >= 0
- Wider when fewer comps
- Level classification correct

**test_validation.py (12 tests):**
- Bedrooms 0-10 accepted
- Bedrooms -1 rejected
- Nightly rate $25-5000 accepted
- Nightly rate $0 rejected
- Address non-empty required

### Task 8.3: Integration Tests (23 tests)
**Files:** `tests/integration/test_*.py`

**test_api_e2e.py (15 tests):**
- Full pipeline: request → response
- Returns 200 for valid input
- Returns 422 for invalid address
- Returns 422 for out-of-NYC address
- Response has all required fields
- Batch endpoint works
- Batch partial failure handled
- Health endpoint returns ok
- Model info endpoint works
- Credits endpoint has attribution

**test_pipeline.py (8 tests):**
- Geocode → comps → features → predict → format
- Error propagation works
- Cache hit improves latency

### Task 8.4: Edge Case Tests (20 tests)
**File:** `tests/edge_cases/test_boundaries.py**

- Jersey City returns error
- Far Rockaway (NYC edge) works
- Studio (bedrooms=0) works
- 10 bedrooms works
- $25/night works (with warning)
- $5000/night works (with warning)
- 16 accommodates works
- Address with special characters
- Duplicate request (cache hit)
- Very long address string

### Task 8.5: Coverage Target
**File:** `pytest.ini`

```ini
[pytest]
addopts = --cov=src --cov-report=term --cov-fail-under=85
testpaths = tests
```

---

## Phase 9: Legal Compliance

### Task 9.1: Attribution
**In:** `templates/index.html`, `src/api.py`, `README.md`

```
Data source: InsideAirbnb (insideairbnb.com)
Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/
Data has been processed and transformed for revenue estimation purposes.
```

### Task 9.2: Disclaimers
**In:** `src/schemas.py`, `templates/index.html`

```
DISCLAIMER: Revenue estimates are provided for informational purposes only
and do not constitute financial, investment, or real estate advice. Estimates
are based on historical data from InsideAirbnb and may not reflect current
market conditions. Actual revenue may vary significantly from estimates.
This tool makes no guarantees of accuracy and shall not be liable for
any decisions made based on these estimates. Past performance does not
guarantee future results. Consult a qualified professional before making
investment decisions.
```

### Task 9.3: PII Stripping
**In:** `scripts/prepare_data.py`

- Remove `host_name` from all data
- Remove `host_location` from all data
- Remove `host_about` from all data
- Remove listing `name` and `description` from API responses
- Use only numeric IDs, never expose listing URLs

### Task 9.4: Privacy Policy
**File:** `README.md` (section)

- What data we collect (address, property specs)
- How we use it (geocoding, prediction)
- How long we keep it (geocode cache: 7 days)
- No data sold to third parties
- GDPR/CCPA considerations

---

## Phase 10: Deployment

### Task 10.1: Requirements
**File:** `requirements.txt`

```
fastapi==0.138.1
uvicorn==0.49.0
pydantic==2.13.4
xgboost==3.3.0
lightgbm==4.6.0
scikit-learn==1.9.0
scipy==1.18.0
pandas==3.0.3
numpy==2.4.6
geopy==2.4.1
cachetools==7.1.4
matplotlib==3.11.0
shap==0.52.0
joblib==1.5.3
python-dotenv==1.0.0
jinja2==3.1.4
```

### Task 10.2: Dockerfile
**File:** `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/prepare_data.py
RUN python scripts/train_model.py
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Task 10.3: Environment Variables
**File:** `.env.example`

```
MAPBOX_TOKEN=your_mapbox_token_here
PORT=8000
LOG_LEVEL=info
CACHE_TTL=604800
```

### Task 10.4: Deploy
1. Push to GitHub
2. Connect to Railway or Fly.io
3. Set environment variables
4. Deploy
5. Verify health endpoint
6. Test with real address

---

## Phase 11: Monitoring

### Task 11.1: Logging
**In:** `src/api.py`

Every request logs:
- Request ID
- Input: address, bedrooms, bathrooms, accommodates, nightly_rate
- Geocoded lat/lng
- Number of comps found
- Prediction: annual_revenue, confidence level
- Latency: geocode_ms, comp_ms, model_ms, total_ms

### Task 11.2: Metrics
Track:
- Request count (total, success, error)
- Geocoder failure rate
- Comp finder returning 0 comps rate
- Prediction distribution (mean, std)
- Latency p50, p95, p99

---

## Build Order (Sequential)

| Step | Task | Time | Depends On |
|------|------|------|------------|
| 1 | prepare_data.py | 30 min | — |
| 2 | train_model.py | 60 min | Step 1 |
| 3 | build_index.py | 15 min | Step 1 |
| 4 | config.py | 10 min | — |
| 5 | schemas.py | 15 min | — |
| 6 | exceptions.py | 10 min | — |
| 7 | validation.py | 15 min | — |
| 8 | geocoder.py | 30 min | Step 4 |
| 9 | comp_finder.py | 45 min | Step 3 |
| 10 | features.py | 30 min | Step 9 |
| 11 | model.py | 20 min | Step 2 |
| 12 | confidence.py | 15 min | Step 9 |
| 13 | api.py | 60 min | Steps 4-12 |
| 14 | index.html | 45 min | Step 13 |
| 15 | style.css | 20 min | Step 14 |
| 16 | app.js | 30 min | Step 14 |
| 17 | conftest.py | 15 min | — |
| 18 | unit tests | 90 min | Steps 8-12 |
| 19 | integration tests | 45 min | Step 13 |
| 20 | edge case tests | 30 min | Step 13 |
| 21 | README.md | 15 min | — |
| 22 | Dockerfile | 10 min | Steps 1-16 |
| 23 | Deploy | 30 min | Step 22 |
| **Total** | | **~10 hours** | |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Model MAPE | <40% |
| Model R² | >0.70 |
| Within 50% of IA | >60% |
| Test coverage | >85% |
| API latency (p50) | <200ms |
| API latency (p99) | <2s |
| Zero PII in responses | ✅ |
| CC BY 4.0 attribution | ✅ |
| Disclaimers in every response | ✅ |
| NYC boundary check working | ✅ |
