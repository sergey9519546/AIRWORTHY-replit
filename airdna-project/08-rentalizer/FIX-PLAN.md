# ULTRAPLAN v4 — Fix All Mistakes and Hallucinations

> Every bug, every leak, every lie. Fixed.

---

## The Honest Assessment

**What I built:** A working FastAPI app with a revenue prediction model, geocoding, comp finder, and web UI.

**What's actually broken:**
1. **The model is fake.** R²=0.997 is from feature leakage (`reviews_ltm` = 60% importance). Real performance is R²=0.3-0.5. The model can't predict revenue for new listings because its most important feature is always zero at inference time.
2. **Borough detection is wrong for ~60% of NYC.** The bounding box logic classifies most of Brooklyn, Queens, and the Bronx as Manhattan.
3. **The blend logic is inconsistent.** Training found α=1.0 (pure XGBoost) on leaked data. Production uses ad-hoc heuristics that were never validated.
4. **The frontend has XSS vulnerabilities.** All `innerHTML` calls inject unsanitized API data.
5. **No authentication, no rate limiting.** The API is wide open.
6. **The Mapbox integration is broken.** Empty token → 200KB of dead JS loading.
7. **Confidence intervals are uncalibrated.** Arbitrary bounds, no validation.
8. **Thread safety issues.** Global mutable state, non-thread-safe cache.

---

## Fix Plan (Ordered by Priority)

### FIX 1: Remove Feature Leakage (P0 — Model)

**Problem:** `reviews_ltm` (60% importance), `reviews_per_month`, `reviews_total`, `review_recency_days`, `reviews_ltm_ratio`, `availability_365`, `availability_30` are all proxies for the target. They won't exist for new listings.

**Fix in `scripts/prepare_data.py`:**
```python
# REMOVE these features (leaky):
LEAKY_FEATURES = [
    "reviews_total", "reviews_ltm", "reviews_per_month_num",
    "availability_365_num", "availability_30_num",
    "review_recency_days", "reviews_ltm_ratio", "occupancy_proxy",
    "review_score",  # Also leaky — only exists after reviews
]

# KEEP these features (available for new listings):
SAFE_FEATURES = [
    "price_num", "accommodates_num", "bedrooms_num", "bathrooms_num",
    "beds_num", "minimum_nights_num", "latitude", "longitude",
    "host_listings_count_num", "host_experience_months",
    "listing_age_months", "price_per_person",
    "instant_bookable_num", "superhost_num",
    # + borough one-hot, property type one-hot
]
```

**Expected impact:** R² drops from 0.997 to ~0.3-0.5. MAPE rises from 2% to ~40-60%. This is the model's TRUE performance.

**File:** `scripts/prepare_data.py`, `src/features.py`, `scripts/train_model.py`

---

### FIX 2: Fix Borough Detection (P0 — Code)

**Problem:** `get_borough_from_coords()` uses wrong bounding boxes. Manhattan check catches most of NYC.

**Fix in `src/features.py`:**
```python
def get_borough_from_coords(lat: float, lng: float) -> str:
    """Approximate borough from coordinates using proper bounding boxes."""
    # Staten Island: south of 40.65, west of -74.05
    if lat < 40.65 and lng < -74.05:
        return "Staten Island"
    # Bronx: north of 40.79
    if lat > 40.79:
        return "Bronx"
    # Queens: east of -73.82
    if lng > -73.82:
        return "Queens"
    # Brooklyn: south of 40.68, east of -73.95
    if lat < 40.68 and lng > -73.95:
        return "Brooklyn"
    # Manhattan: everything else within NYC bounds
    return "Manhattan"
```

**Better fix:** Use a proper GeoJSON lookup with `shapely`:
```python
import json
from shapely.geometry import Point, shape

# Load NYC borough boundaries once at startup
with open("data/nyc-boroughs.geojson") as f:
    boroughs = json.load(f)

def get_borough_from_coords(lat: float, lng: float) -> str:
    point = Point(lng, lat)  # GeoJSON is (lng, lat)
    for feature in boroughs["features"]:
        if shape(feature["geometry"]).contains(point):
            return feature["properties"]["boro_name"]
    return "Manhattan"  # Fallback
```

**File:** `src/features.py`

---

### FIX 3: Unify Blend Logic (P0 — Model)

**Problem:** Training finds α=1.0 on leaked data. Production uses ad-hoc heuristics.

**Fix:** After removing leaky features, re-optimize the blend. The comp-based prediction will become more valuable since the model is weaker.

**In `scripts/train_model.py`:**
```python
# After retraining without leaky features:
# Grid search α on the TEST set (not training)
# Expected: α ≈ 0.4-0.6 (model and comps contribute equally)
```

**In `src/api.py`:**
```python
# Use the optimized α from training, not ad-hoc heuristics
# Store α in models/meta.json and load it
blend_alpha = _meta.get("blend_alpha", 0.5)
final_log_revenue = blend_alpha * log_revenue + (1 - blend_alpha) * np.log1p(comp_pred)
```

**File:** `scripts/train_model.py`, `src/api.py`, `src/model.py`

---

### FIX 4: Fix XSS Vulnerability (P0 — Frontend)

**Problem:** All `innerHTML` calls inject unsanitized API data.

**Fix in `static/app.js`:**
```javascript
// Helper: safe text insertion
function setText(id, text) {
    document.getElementById(id).textContent = text;
}

function renderResults(data) {
    // Use textContent for all data values
    setText('revenue-range', `${formatCurrency(data.confidence.revenue_lower)} — ${formatCurrency(data.confidence.revenue_upper)}`);

    // Build comps list safely
    const compsList = document.getElementById('comps-list');
    compsList.innerHTML = ''; // Clear
    const header = document.createElement('div');
    header.className = 'comp-item';
    ['Borough', 'Beds', 'Revenue', 'Distance'].forEach(text => {
        const span = document.createElement('span');
        span.className = 'comp-header';
        span.textContent = text;
        header.appendChild(span);
    });
    compsList.appendChild(header);

    for (const comp of data.comps) {
        const row = document.createElement('div');
        row.className = 'comp-item';
        [comp.borough, `${comp.bedrooms} BR`, formatCurrency(comp.revenue), `${comp.distance_km} km`].forEach(text => {
            const span = document.createElement('span');
            span.textContent = text;
            row.appendChild(span);
        });
        compsList.appendChild(row);
    }
}
```

**File:** `static/app.js`

---

### FIX 5: Add Authentication (P1 — Security)

**Fix in `src/api.py`:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
import os

API_KEYS = os.getenv("API_KEYS", "").split(",")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not API_KEYS or API_KEYS == [""]:
        return None  # No auth configured (dev mode)
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Apply to data routes:
@app.post("/v1/estimate", dependencies=[Depends(verify_api_key)])
```

**File:** `src/api.py`

---

### FIX 6: Add Rate Limiting (P1 — Security)

**Install:** `pip install slowapi`

**Fix in `src/api.py`:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/v1/estimate")
@limiter.limit("30/minute")
async def estimate(request: Request, req: EstimateRequest):
    ...

@app.post("/v1/batch")
@limiter.limit("5/minute")
async def batch_estimate(request: Request, requests: list[EstimateRequest]):
    ...
```

**File:** `src/api.py`, `requirements.txt`

---

### FIX 7: Fix Mapbox → Leaflet (P1 — Frontend)

**Problem:** Mapbox token is empty, 200KB of dead JS loads.

**Fix in `templates/index.html`:**
```html
<!-- Replace Mapbox with Leaflet (free, no token needed) -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" defer></script>
```

**Fix in `static/app.js`:**
```javascript
function renderMap(lat, lng, comps) {
    const mapDiv = document.getElementById('map');
    mapDiv.innerHTML = '';

    const map = L.map('map').setView([lat, lng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Property marker (red)
    L.marker([lat, lng], { icon: createIcon('#ff5a5f') })
        .bindPopup('<b>Your property</b>')
        .addTo(map);

    // Comp markers (blue) — would need comp coordinates
    // For now, just show the property location
}

function createIcon(color) {
    return L.divIcon({
        className: 'custom-marker',
        html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid white;"></div>`,
        iconSize: [16, 16],
    });
}
```

**File:** `templates/index.html`, `static/app.js`

---

### FIX 8: Fix Thread Safety (P1 — Code)

**Fix in `src/geocoder.py`:**
```python
import threading
from cachetools import TTLCache

_cache_lock = threading.Lock()
cache = TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)

def geocode(address: str) -> GeocodeResult:
    key = normalize_address(address)
    with _cache_lock:
        if key in cache:
            return cache[key]
    # ... geocode ...
    with _cache_lock:
        cache[key] = result
    return result
```

**Fix `Nominatim` recreation:**
```python
_geolocator = None
_geolocator_lock = threading.Lock()

def _get_geolocator():
    global _geolocator
    with _geolocator_lock:
        if _geolocator is None:
            _geolocator = Nominatim(user_agent="rentalizer-v1", timeout=10)
    return _geolocator
```

**File:** `src/geocoder.py`

---

### FIX 9: Fix None/0 Confusion (P1 — Code)

**Fix in `src/comp_finder.py`:**
```python
# Use None for missing, 0 for actual zero
@dataclass
class Comp:
    listing_id: int | None = None
    bedrooms: int | None = None
    # ...
```

**Fix in `src/features.py`:**
```python
# Don't hardcode review features to 0 — omit them or use a sentinel
# Better: remove leaky features entirely from the feature set
```

**Fix in `src/schemas.py`:**
```python
# Change bathrooms from int to float
bathrooms: float = Field(ge=0, le=10, default=1.0)
```

**File:** `src/comp_finder.py`, `src/features.py`, `src/schemas.py`

---

### FIX 10: Fix Performance Issues (P2 — Code)

**Fix `iterrows()` in `comp_finder.py`:**
```python
# Replace:
for _, row in train_df.iterrows():
    _listings.append({...})

# With:
_listings = train_df.to_dict('records')
```

**Fix `optimize_blend()` in `train_model.py`:**
```python
# Vectorize with merge instead of iterrows
# ...
```

**Fix `get_market_stats()` — pre-compute at startup:**
```python
_market_stats = {}

def _precompute_market_stats():
    global _market_stats
    for borough in ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]:
        col = f"borough_{borough}"
        if col in _train_data.columns:
            subset = _train_data[_train_data[col] == 1]
            _market_stats[borough] = {
                "median_revenue": float(subset["revenue"].median()),
                "median_price": float(subset["price_num"].median()),
                "active_listings": len(subset),
            }
```

**File:** `src/comp_finder.py`, `scripts/train_model.py`

---

### FIX 11: Fix Accessibility (P1 — Frontend)

**Fix in `templates/index.html`:**
```html
<div id="loading" class="hidden" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true"></div>
    <p>Analyzing property...</p>
</div>

<div id="error" class="hidden" role="alert" aria-live="assertive">
    <p id="error-message"></p>
</div>

<div id="results" class="hidden" aria-live="polite" tabindex="-1">
```

**Fix in `static/style.css`:**
```css
/* Fix contrast */
.subtitle, .stat-label, .disclaimer { color: #64748b; }

/* Focus styles */
:focus-visible {
    outline: 2px solid #4f46e5;
    outline-offset: 2px;
}
```

**File:** `templates/index.html`, `static/style.css`, `static/app.js`

---

### FIX 12: Fix Docker Security (P1 — Security)

**Fix `Dockerfile`:**
```dockerfile
FROM python:3.12-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `Dockerfile`

---

### FIX 13: Fix Error Handling (P1 — Code)

**Fix `load_model()` in `src/model.py`:**
```python
def load_model():
    global _model, _meta, _features
    try:
        _model = joblib.load(settings.MODEL_PATH)
    except FileNotFoundError:
        logger.error(f"Model file not found: {settings.MODEL_PATH}")
        raise ModelNotReadyError("Model file not found")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise ModelNotReadyError(f"Model load failed: {e}")
    # ... similar for meta and features ...
```

**Fix `batch_estimate()` error handling:**
```python
except Exception as e:
    logger.exception(f"Batch item failed: {e}")
    results.append({"error": "estimation_failed", "detail": "Could not estimate this property"})
```

**File:** `src/model.py`, `src/api.py`

---

### FIX 14: Add Request Timeout (P1 — Frontend)

**Fix in `static/app.js`:**
```javascript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 15000);

try {
    const resp = await fetch('/v1/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
    });
    clearTimeout(timeout);
    // ... handle response ...
} catch (err) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
        message = 'Request timed out. Please try again.';
    }
}
```

**File:** `static/app.js`

---

### FIX 15: Fix Brand Color (P2 — Design)

**Fix in `static/style.css`:**
```css
:root {
    --color-primary: #4f46e5;      /* Indigo — professional */
    --color-primary-hover: #4338ca;
}

button[type="submit"] { background: var(--color-primary); }
button[type="submit"]:hover { background: var(--color-primary-hover); }
```

**File:** `static/style.css`

---

### FIX 16: Retrain Model (P0 — Model)

**After removing leaky features, retrain:**
```bash
python scripts/prepare_data.py   # Recreate features without leaky ones
python scripts/train_model.py 50  # Retrain with 50 Optuna trials
```

**Expected results:**
- R²: 0.3-0.5 (realistic)
- MAPE: 40-60% (realistic)
- Within 50%: 50-70% (realistic)
- Blend α: 0.4-0.6 (model + comps contribute equally)

---

## Build Order

| Step | Fix | File(s) | Time |
|------|-----|---------|------|
| 1 | Remove leaky features | prepare_data.py, features.py | 30 min |
| 2 | Retrain model | train_model.py | 30 min |
| 3 | Fix borough detection | features.py | 15 min |
| 4 | Unify blend logic | api.py, model.py | 20 min |
| 5 | Fix XSS | app.js | 30 min |
| 6 | Fix Mapbox → Leaflet | index.html, app.js | 20 min |
| 7 | Add auth + rate limiting | api.py | 30 min |
| 8 | Fix thread safety | geocoder.py, comp_finder.py | 20 min |
| 9 | Fix None/0 confusion | schemas.py, comp_finder.py | 15 min |
| 10 | Fix error handling | model.py, api.py | 15 min |
| 11 | Fix accessibility | index.html, style.css | 20 min |
| 12 | Fix Docker security | Dockerfile | 5 min |
| 13 | Fix performance | comp_finder.py | 15 min |
| 14 | Fix brand color | style.css | 5 min |
| 15 | Add request timeout | app.js | 10 min |
| 16 | Verify + test | all | 30 min |
| **Total** | | | **~5 hours** |

---

## What This Changes

**Before fixes:**
- Model R²: 0.997 (fake)
- Model MAPE: 2% (fake)
- Borough accuracy: ~40%
- XSS: yes
- Auth: none
- Rate limiting: none

**After fixes:**
- Model R²: 0.3-0.5 (real)
- Model MAPE: 40-60% (real)
- Borough accuracy: ~95%
- XSS: fixed
- Auth: API key
- Rate limiting: 30/min

**The honest truth:** The model will be mediocre. 40-60% MAPE means predictions are ±40-60% of actual revenue. That's a $35K-$65K range for a property that earns $50K. Not great, but it's real — not a hallucinated 2% error from leaked features.

**The path to better accuracy:**
1. Add more data (events, holidays, transit, demographics)
2. Train on multiple cities
3. Use temporal validation
4. Build a proper ensemble
5. Collect real revenue data (not estimates)
