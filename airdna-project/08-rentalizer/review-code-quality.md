# Code Quality Audit — Rentalizer

**Auditor:** Senior Python Engineer  
**Date:** 2026-06-29  
**Files reviewed:** 12 (src/*.py + scripts/*.py)  
**Severity scale:** 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low · ⚪ Style

---

## Executive Summary

The codebase is **functional but fragile**. It works for the happy path but has real bugs in the borough detection logic, silent data corruption risks, thread-safety issues with global state, and several places where exceptions are swallowed. The biggest systemic problem is **pervasive use of `None` vs `0` ambiguity** — many functions return `None` when they should return a typed sentinel or raise.

---

## 1. BUGS

### 🔴 B1 — `get_borough_from_coords()` has wrong bounding boxes (features.py:82–90)

```python
def get_borough_from_coords(lat: float, lng: float) -> str:
    if lat > 40.70 and lng > -74.02:
        return "Manhattan"
    elif lat > 40.57 and lng > -73.95:
        return "Brooklyn"
    elif lat > 40.65 and lng < -73.75:
        return "Queens"
    elif lat > 40.80:
        return "Bronx"
    else:
        return "Manhattan"  # Default
```

**Problems:**
- **Manhattan check is too broad.** Anything with `lat > 40.70` AND `lng > -74.02` returns Manhattan. This catches most of Brooklyn, Queens, and the Bronx too (they all have `lng > -74.02`). The conditions are not mutually exclusive — the first match wins, so Brooklyn/Queens/Bronx are effectively dead code for most inputs.
- **Staten Island is never returned.** There is no condition for it.
- **Default fallback to Manhattan** masks errors. A coordinate in New Jersey that passes the NYC bounds check (which is a very loose bounding box) would be classified as Manhattan.
- **One-hot encoding mismatch:** The borough label flows into `build_features()` which creates `borough_Manhattan` etc. If the borough string doesn't exactly match one of `["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]`, all borough columns are 0. The function guarantees one of these, but the logic is wrong for most coordinates.

**Impact:** Wrong borough → wrong one-hot features → biased model prediction. Every Brooklyn, Queens, and Bronx listing with `lat > 40.70` gets misclassified as Manhattan.

### 🔴 B2 — `_find_comps_relaxed()` can crash on empty `_listings` (comp_finder.py:97–118)

```python
def _find_comps_relaxed(lat: float, lng: float, k: int) -> list[Comp]:
    query = np.radians([[lat, lng]])
    distances, indices = _tree.query(query, k=min(k, len(_listings)))
```

If `_listings` is empty (e.g., `build_index` was called with an empty DataFrame), `len(_listings)` = 0, and `KDTree.query(k=0)` raises `ValueError`. The caller `find_comps()` does check `_tree is None` but not for empty index.

### 🟠 B3 — `optimize_blend()` iterates test set with O(n×m) complexity (train_model.py:148–170)

```python
for i, (_, row) in enumerate(test.iterrows()):
    same_borough = train[[c for c in train.columns if ...]]
    borough_match = train
    for col in same_borough.columns:
        if row.get(col, 0) == 1:
            borough_match = train[train[col] == 1]
    bed_match = borough_match[...]
```

**Bugs within the bug:**
- `row.get(col, 0)` — `row` is a pandas Series from `iterrows()`. Series `.get()` works but the default `0` is compared to `== 1`, which is fine. However, if a borough column has value `True` (bool) instead of `1` (int), `row.get(col, 0) == 1` is `False`, silently skipping all borough filtering.
- The `for col in same_borough.columns` loop **overwrites** `borough_match` on each iteration. If a listing matches multiple borough columns (data bug), only the last match survives. If none match, `borough_match = train` (all data).
- This is an **O(test × train)** loop with DataFrame filtering inside. For 5000 test rows and 20k training rows, this is ~100M operations. Should vectorize.

### 🟠 B4 — `batch_estimate` catches too broadly (api.py:168–175)

```python
for req in requests:
    try:
        result = await estimate(req)
        results.append(result.model_dump())
    except Exception as e:
        results.append({"error": type(e).__name__, "detail": str(e)})
```

This catches **all** exceptions including `KeyboardInterrupt` (via `BaseException` → no, `Exception` doesn't catch `KeyboardInterrupt`). But it does catch things like `MemoryError`, `SystemExit`, and `GeneratorExit` which inherit from `BaseException` — actually no, those inherit from `BaseException`, not `Exception`. So this is fine for those. However, the pattern still swallows important errors silently and returns them as data. A `TypeError` from a bug in the pipeline becomes a "normal" error response. The batch endpoint should distinguish between expected validation errors and unexpected crashes.

### 🟠 B5 — `predict_from_comps()` returns `None` silently (comp_finder.py:137–146)

```python
def predict_from_comps(comps: list[Comp]) -> tuple[float | None, float]:
    if not comps:
        return None, 1.0
```

Caller in `api.py:107`:
```python
comp_revenue = float(comp_pred) if comp_pred is not None else None
```

If `comp_pred` is `None`, then `comp_revenue` is `None`, and the blending logic is skipped entirely. But there's no logging or warning — the model prediction is used raw without any indication that comp-based blending was unavailable. For a property with zero comps (unlikely but possible), the user gets a model-only prediction with no signal that it's less reliable.

### 🟡 B6 — `Nominatim` geocoder created on every call (geocoder.py:70–76)

```python
def _geocode_nominatim(address: str) -> GeocodeResult | None:
    geolocator = Nominatim(user_agent="rentalizer-v1", timeout=10)
```

`Nominatim()` creates a new session/connection pool on every invocation. Should be module-level. Not a crash bug, but wasteful and may hit rate limits faster.

### 🟡 B7 — Mapbox URL not URL-encoded (geocoder.py:52)

```python
url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
```

Addresses with special characters (`#`, `&`, `?`, spaces) will break the URL. Should use `urllib.parse.quote(address)`.

---

## 2. TYPE SAFETY

### 🔴 T1 — `None` vs `0` confusion throughout

| Location | Issue |
|---|---|
| `comp_finder.py:67` | `row.get("id", 0)` — `id=0` is a valid-looking but meaningless ID |
| `comp_finder.py:69` | `row.get("bedrooms_num", 0)` — 0 bedrooms is a studio, semantically different from "missing" |
| `comp_finder.py:70` | `row.get("bathrooms_num", 1)` — default 1 bathroom, but if column is missing, this is a guess |
| `features.py:17–19` | `reviews_total = 0`, `reviews_ltm = 0` — these are used as features. `0` means "no reviews" but also "data missing". The model can't distinguish. |
| `confidence.py:22` | `revenue_lower=max(0, prediction * 0.5)` — if `prediction` is `0` or negative (possible with `expm1` of small log values), `revenue_lower = 0` and `revenue_upper = 0`. |
| `model.py:50` | `features.get(f, 0)` — missing features silently become 0. If a feature name changes between training and inference, this silently corrupts predictions. |

### 🟠 T2 — `build_features()` returns `dict` not aligned with model expectations (features.py:7–75)

The function builds a `dict` then re-maps it to `vector` using `feature_columns`. If `feature_columns` contains a column name not present in `features`, it silently gets `0`. If `features` has extra keys, they're silently dropped. There's no validation that the two lists match.

### 🟡 T3 — `EstimateRequest.bathrooms` is `int` but real bathrooms can be 1.5 (schemas.py:11)

```python
bathrooms: int = Field(ge=0, le=10, default=1)
```

Half-baths are common in NYC. This should be `float`.

### 🟡 T4 — `_score_comp()` always returns full bathroom score (comp_finder.py:125)

```python
bath_score = 0.15  # Default full score since we don't have target bathrooms
```

The function signature doesn't accept `target_bathrooms`. The comment acknowledges this but it means 15% of the score is wasted — every comp gets the same bathroom score, making it meaningless.

---

## 3. ERROR HANDLING

### 🔴 E1 — `load_model()` has no error handling (model.py:20–32)

```python
def load_model():
    global _model, _meta, _features
    _model = joblib.load(settings.MODEL_PATH)
    with open(settings.META_PATH) as f:
        _meta = json.load(f)
    with open(settings.FEATURES_PATH) as f:
        _features = json.load(f)["features"]
```

If any file is missing or corrupted, the app crashes on startup with an unhelpful traceback. Should catch `FileNotFoundError`, `json.JSONDecodeError`, and `joblib` exceptions with clear error messages.

### 🟠 E2 — `geocode()` swallows all Mapbox exceptions (geocoder.py:38–43)

```python
try:
    result = _geocode_mapbox(address)
    if result:
        cache[key] = result
        return result
except Exception as e:
    logger.warning(f"Mapbox geocoding failed: {e}")
```

This catches **everything** — network timeouts, auth errors, rate limits, JSON decode errors. A 401 (invalid token) will be retried on every request forever. Should at least distinguish between transient (timeout, 429) and permanent (401, 403) failures.

### 🟠 E3 — `build_index()` has no validation (comp_finder.py:25–50)

No check that the DataFrame has required columns (`latitude`, `longitude`, `price_num`, `revenue`). If any column is missing, it fails with a cryptic `KeyError` deep in the loop.

### 🟡 E4 — `_geocode_mapbox` doesn't check HTTP status for partial errors (geocoder.py:55–65)

`resp.raise_for_status()` catches 4xx/5xx, but Mapbox can return 200 with an empty features list (no results). This is handled by the `if not features: return None` check, which is correct. However, a 200 with a malformed response (missing `center` key) will raise an unhandled `KeyError`.

---

## 4. PERFORMANCE

### 🔴 P1 — `build_index()` uses `iterrows()` (comp_finder.py:40–50)

```python
for _, row in train_df.iterrows():
    _listings.append({...})
```

`iterrows()` is the slowest way to iterate a DataFrame. For 20k+ rows, this is noticeable at startup. Should use `train_df.to_dict('records')` or vectorized column operations.

### 🟠 P2 — `_find_comps_relaxed()` re-queries the full KD-Tree (comp_finder.py:97–118)

When the main `find_comps()` finds <3 comps, it calls `_find_comps_relaxed()` which does a **second** KD-Tree query. This doubles the work for edge cases. Should query once with a larger `k` and filter.

### 🟠 P3 — `optimize_blend()` is O(n×m) with DataFrame operations inside (train_model.py:148–170)

Already noted in B3. For a training script this is tolerable, but it could be vectorized with `merge` operations.

### 🟡 P4 — `get_market_stats()` creates boolean mask on every call (comp_finder.py:152–165)

```python
mask = _train_data[borough_col] == 1
subset = _train_data[mask]
```

This filters the entire DataFrame on every API call. Should pre-compute borough groupings at index build time.

### 🟡 P5 — `batch_estimate` is sequential (api.py:165–175)

Each request in the batch is awaited sequentially. For large batches, this is slow. Could use `asyncio.gather()` with a semaphore for concurrency control.

---

## 5. THREAD SAFETY

### 🔴 S1 — Global mutable state in `comp_finder.py` (lines 22–24)

```python
_tree: KDTree | None = None
_train_data: pd.DataFrame | None = None
_listings: list[dict] | None = None
```

These are written once at startup (`build_index()`) and read from async request handlers. **This is safe as long as:**
- `build_index()` completes before any requests are served (the `lifespan` context manager ensures this)
- No one calls `build_index()` again at runtime

However, there's **no lock or protection** against concurrent reads during a hypothetical re-index. If you ever add a hot-reload endpoint, this becomes a race condition.

### 🟡 S2 — Global mutable state in `model.py` (lines 12–14)

Same pattern as above. Same risk profile.

### 🟡 S3 — `geocoder.py` cache is not thread-safe (line 17)

```python
cache = TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)
```

`cachetools.TTLCache` is **not thread-safe**. In a multi-threaded ASGI server (e.g., uvicorn with workers > 1), concurrent access to the cache can corrupt internal state. Use `cachetools.cached` with a lock, or `threading.Lock` around cache access.

---

## 6. RESOURCE LEAKS

### 🟡 R1 — File handles in `model.py` not using context managers properly (model.py:26–31)

```python
with open(settings.META_PATH) as f:
    _meta = json.load(f)
```

Actually these **do** use context managers (`with`), so this is fine. No leak here. ✅

### 🟡 R2 — `requests.get()` in `_geocode_mapbox` has no connection pooling (geocoder.py:54)

Each call creates a new `requests.Session` implicitly. Should use a module-level `requests.Session()` for connection reuse, especially under load.

---

## 7. IMPORT ISSUES

### 🟡 I1 — `import os` in the middle of `api.py` (line 38)

```python
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

All other imports are at the top. This is a style issue but also a sign of copy-paste.

### 🟡 I2 — Lazy import in `ready()` endpoint (api.py:180–182)

```python
@app.get("/v1/ready")
async def ready():
    from .model import _model as m
    from .comp_finder import _tree as t
```

Accessing private globals (`_model`, `_tree`) via import is fragile. If the module is reloaded or the global is renamed, this breaks silently. Should use the public accessor functions (`get_model_info()`, etc.).

### ⚪ I3 — `import requests` inside `_geocode_mapbox` (geocoder.py:53)

```python
def _geocode_mapbox(address: str) -> GeocodeResult | None:
    import requests
```

Lazy import to avoid import when Mapbox is not configured. Fine, but unconventional. Consider a top-level try/except import.

---

## 8. EDGE CASES

### 🔴 E8-1 — Zero comps and low model confidence

If `find_comps()` returns empty (possible for very remote NYC locations), then:
- `predict_from_comps()` returns `(None, 1.0)`
- `comp_revenue = None`
- Blending is skipped
- `confidence = compute_confidence(annual_revenue, [], 0)` → returns "low" with `revenue_lower = prediction * 0.5`

This works but gives no signal to the user that the estimate is based purely on model output with no market validation.

### 🟠 E8-2 — Negative `expm1` output

If `log_revenue` is very negative (e.g., -5), then `expm1(-5) ≈ -0.993`. The code does `annual_revenue = float(np.expm1(final_log_revenue))` which can be negative. The API would return a negative annual revenue. There's no guard against this.

### 🟠 E8-3 — `comp_median = 0` in blending logic (api.py:116)

```python
comp_median = np.median([c.revenue for c in comps]) if comps else 0
if model_revenue < comp_median * 0.3:
```

If `comp_median = 0`, then `comp_median * 0.3 = 0`, and `model_revenue < 0` is the only way to trigger the first branch. But if comps exist, their revenues should be positive. However, if data has zero-revenue listings that slipped through, this breaks.

### 🟡 E8-4 — Very large nightly rate

`EstimateRequest` allows `nightly_rate` up to 10000, but `validate_input()` only warns about rates > `$5000`. A $10,000/night listing will get a warning but the model will extrapolate wildly since training data likely maxes out around $1000–2000.

### 🟡 E8-5 — `accommodates=1` with `beds_num = max(1, accommodates // 2)` = 1

This is fine, but `accommodates=20` gives `beds_num=10`, which is reasonable. The `max(1, ...)` prevents zero beds.

---

## 9. CODE QUALITY

### 🟡 Q1 — `build_features()` has duplicated code blocks (features.py:22–55)

The `if comps:` and `else:` branches set **identical** values. The entire conditional is dead logic — the `else` branch could be removed and the defaults used unconditionally.

### 🟡 Q2 — Magic numbers everywhere

| Location | Value | Meaning |
|---|---|---|
| `comp_finder.py:86` | `k * 3` | Over-fetch factor for KD-Tree |
| `comp_finder.py:108` | `20` | Max relaxed search radius (km) |
| `comp_finder.py:122` | `10` | Max distance for scoring |
| `api.py:112` | `0.3`, `0.6` | Blend thresholds |
| `api.py:115` | `0.2` | Low-confidence alpha |
| `confidence.py:30` | `0.7`, `1.3` | CI blend factors |
| `features.py:82–90` | All coordinates | Borough bounding boxes |

These should be named constants in `config.py`.

### 🟡 Q3 — `_get_borough()` in comp_finder.py is fragile (line 55–60)

```python
for col in ["borough_Manhattan", "borough_Brooklyn", ...]:
    if row.get(col, 0) == 1:
        return col.replace("borough_", "")
return "Unknown"
```

If a listing has no borough column (data issue), it returns `"Unknown"`. But `build_features()` in `features.py` only one-hot encodes the five known boroughs — `"Unknown"` produces all zeros. This is consistent but means the model sees a borough-less listing as having no borough signal.

### ⚪ Q4 — Inconsistent logging

Some modules use `logger.info()`, some use `print()` (scripts), some use `logger.warning()`. The API module logs request details at INFO level, which is fine for production but very noisy.

### ⚪ Q5 — `train_model.py` mutates `train` DataFrame in `baseline_median()` (line 97)

```python
train["borough_label"] = train[borough_col].idxmax(axis=1).str.replace("borough_", "")
```

This adds a column to the DataFrame that persists for subsequent functions. If `optimize_blend()` or later functions check columns, they'll see `borough_label` which wasn't there before. Should use `.copy()` or drop the column after use.

---

## 10. REFACTORING OPPORTUNITIES

### R1 — Extract borough detection to a proper module

`get_borough_from_coords()` in `features.py` and `_get_borough()` in `comp_finder.py` serve the same purpose with different implementations. The coordinate-based one is wrong (see B1). The column-based one is correct but only works on training data. Unify into a single, correct implementation.

**Suggestion:** Use a proper point-in-polygon lookup with NYC borough shapefiles, or at minimum fix the bounding boxes using real data:
- Manhattan: lat 40.70–40.88, lng -74.02 to -73.91
- Brooklyn: lat 40.57–40.74, lng -74.05 to -73.85
- Queens: lat 40.55–40.80, lng -73.96 to -73.70
- Bronx: lat 40.79–40.92, lng -73.93 to -73.77
- Staten Island: lat 40.50–40.65, lng -74.26 to -74.05

### R2 — Pre-compute market stats at startup

`get_market_stats()` filters the training DataFrame on every API call. Pre-compute a `borough_stats` dict in `build_index()`.

### R3 — Add input validation for feature completeness

`predict()` should verify that all expected features are present in the input dict, not silently defaulting to 0.

### R4 — Use Pydantic `model_validator` for cross-field validation

`EstimateRequest` validates individual fields but not relationships (e.g., `accommodates` should be ≥ `bedrooms + 1` for most properties).

### R5 — Separate blending logic from the endpoint

The blending logic in `api.py:105–125` is complex business logic embedded in a route handler. Extract to a `blender.py` module for testability.

### R6 — `train_model.py` blend optimization is throwaway

The `optimize_blend()` function computes a blend alpha but the saved model doesn't use it at inference time. The API has its own blending logic (api.py:105–125) that's different from the training-time blend. This is a training/inference mismatch — the model was optimized with one blending strategy but deployed with another.

---

## 11. SUMMARY TABLE

| Severity | Count | Key Themes |
|---|---|---|
| 🔴 Critical | 4 | Borough detection wrong, silent data corruption, no startup validation |
| 🟠 High | 6 | Exception swallowing, O(n²) training loop, missing guards |
| 🟡 Medium | 12 | Thread safety, duplicated code, magic numbers, type issues |
| 🟢 Low | 4 | Style, lazy imports, logging inconsistency |
| **Total** | **26** | |

---

## 12. RECOMMENDED PRIORITY FIXES

1. **Fix `get_borough_from_coords()`** — This silently corrupts predictions for ~60% of NYC listings. Use proper bounding boxes or a shapefile.
2. **Add startup validation** — Verify model files exist and are parseable before accepting requests.
3. **Guard against negative revenue** — Add `max(0, ...)` before returning annual revenue.
4. **URL-encode Mapbox addresses** — One-line fix, prevents geocoding failures for addresses with special chars.
5. **Make cache thread-safe** — Wrap `TTLCache` with a lock for multi-worker deployments.
6. **Remove duplicate code in `build_features()`** — The `if comps:` / `else:` branches are identical.
7. **Extract blending logic** — Move from api.py to a testable module.
8. **Add feature completeness check** — Validate that inference features match training features.
