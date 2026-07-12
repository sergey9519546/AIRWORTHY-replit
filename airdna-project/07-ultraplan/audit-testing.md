# Testing Audit — Rentalizer Revenue Prediction Engine

**Auditor:** Senior QA Engineer  
**Date:** 2026-06-29  
**Scope:** PLAN.md testing strategy review  
**Verdict:** 🔴 SIGNIFICANT GAPS — Plan is model-centric with almost no testing strategy

---

## Executive Summary

The plan is a solid data science blueprint but a **poor engineering blueprint**. It describes *what to build* and *how to evaluate the model* but treats testing as an afterthought. The `tests/` directory contains two stubs (`test_model.py`, `test_api.py`) with zero detail on what goes in them. There is no testing strategy document, no edge case analysis, no contract testing, no load testing, no monitoring plan. This audit fills those gaps.

**Critical finding:** The plan conflates *model evaluation* (MAPE, R², CV) with *software testing* (unit, integration, contract, edge case). These are fundamentally different disciplines. A model with MAPE < 40% can still crash on `bedrooms=0`, return garbage for addresses in New Jersey, or leak training data through the comp finder.

---

## 1. Is the Testing Strategy Complete?

### What EXISTS in the plan:
- ✅ Model evaluation metrics (MAPE, R², MAE, Within-25%, Within-50%)
- ✅ 5-fold cross-validation
- ✅ Holdout test set
- ✅ 10-listing real-world comparison
- ✅ Mentions `tests/test_model.py` and `tests/test_api.py` in file structure

### What is MISSING:

| Category | Gap | Severity |
|----------|-----|----------|
| **Unit tests** | Zero unit test specifications for any module | 🔴 Critical |
| **Integration tests** | No end-to-end test from API request → JSON response | 🔴 Critical |
| **Edge cases** | No boundary/invalid input testing defined | 🔴 Critical |
| **Geocoder testing** | No strategy for mocking Nominatim | 🔴 Critical |
| **Contract tests** | No response schema validation | 🟡 High |
| **Performance tests** | No latency/throughput targets | 🟡 High |
| **Regression tests** | No plan for detecting model degradation | 🟡 High |
| **Data validation** | No tests for input data quality | 🟡 High |
| **Error handling** | No test for graceful failure modes | 🟡 High |
| **Security tests** | No input sanitization testing | 🟡 Medium |
| **Load tests** | No concurrent user testing | 🟢 Low (MVP) |

### Recommended Minimum Test Suite:

```
tests/
├── unit/
│   ├── test_geocoder.py          # 15+ tests
│   ├── test_comp_finder.py       # 20+ tests
│   ├── test_feature_engineering.py # 15+ tests
│   ├── test_model_predict.py     # 10+ tests
│   ├── test_confidence.py        # 8+ tests
│   └── test_data_validation.py   # 10+ tests
├── integration/
│   ├── test_api_e2e.py           # 15+ tests
│   ├── test_geocoder_real.py     # 5+ tests (optional, network)
│   └── test_model_pipeline.py    # 5+ tests
├── contract/
│   └── test_response_schema.py   # 10+ tests
├── edge_cases/
│   └── test_boundaries.py        # 20+ tests
└── performance/
    └── test_latency.py           # 5+ tests
```

**Target: 150+ test cases minimum. The plan's two stub files are woefully inadequate.**

---

## 2. How Do We Test the Geocoder? Mock or Real API?

### The Plan Says:
> "Use Nominatim (free, no API key). Cache geocoding results. Fallback: Mapbox if Nominatim fails."

### The Problem:
The plan says **nothing** about testing the geocoder. This is a critical external dependency that:
- Has rate limits (1 req/sec for Nominatim)
- Can return ambiguous results ("Spring St" → which city?)
- Can fail entirely (network down, API changes)
- Returns different results over time (addresses get re-geocoded)

### Recommended Strategy: **Both. Layered.**

#### Layer 1: Unit Tests with Mocked Responses (REQUIRED)
```python
# Mock Nominatim responses for known addresses
# Test that geocoder correctly:
# - Parses "350 5th Ave, New York, NY" → correct lat/lng
# - Handles missing apartment numbers gracefully
# - Normalizes "St" vs "Street", "Ave" vs "Avenue"
# - Returns structured error for unparseable addresses
# - Handles Nominatim returning multiple results (pick best)
# - Handles Nominatim returning zero results
# - Retries on 429 (rate limit) with backoff
# - Falls back to Mapbox when Nominatim is down
```

**Mock fixtures:** Store 50+ real Nominatim response JSONs covering:
- Standard NYC addresses (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- Edge cases: "Times Square", "JFK Airport", "Central Park"
- Ambiguous: "123 Main St" (which borough?)
- Invalid: "", "asdfghjkl", "Paris, France"

#### Layer 2: Integration Tests Against Real Nominatim (OPTIONAL, CI-flagged)
```python
@pytest.mark.network
def test_geocode_real_empire_state():
    """Verify Nominatim still returns correct coords for Empire State Building."""
    result = geocode("350 5th Ave, New York, NY 10118")
    assert abs(result.lat - 40.7484) < 0.001
    assert abs(result.lng - (-73.9857)) < 0.001
```

Run these in CI with `--run-network` flag. They catch Nominatim API drift.

#### Layer 3: Contract Tests for Response Shape
```python
def test_geocode_response_shape():
    """Every geocode result must have lat, lng, display_name, confidence."""
    mock_nominatim(return_valid_response())
    result = geocode("350 5th Ave, New York, NY")
    assert hasattr(result, 'lat')
    assert hasattr(result, 'lng')
    assert hasattr(result, 'display_name')
    assert isinstance(result.lat, float)
    assert isinstance(result.lng, float)
```

### ⚠️ Critical Edge Case the Plan Ignores:
**What happens when the geocoded point is in the middle of the East River?** Nominatim sometimes returns centroid coordinates for vague addresses. The comp finder will find "comps" that are technically nearby but semantically wrong. Need a **water/land boundary check** or at minimum a "geocode confidence" score.

---

## 3. How Do We Test the Model? What's the Ground Truth?

### The Plan Says:
> "Target: `estimated_revenue_l365d` from InsideAirbnb"
> "MAPE < 40%, Within 50% > 60%"

### The Problem:
**The ground truth itself is an estimate.** InsideAirbnb's `estimated_revenue_l365d` is derived from price × estimated occupancy. It is NOT actual revenue. This means:

1. **Your model is predicting a prediction.** Errors compound.
2. **You can never validate against actual revenue** without a data partnership with Airbnb or a scraping operation.
3. **The 40% MAPE target is against an already-noisy label.** True real-world error could be 60%+.

### What the Plan Should Include:

#### A. Label Quality Analysis
```python
# Before training, validate the label:
# - Distribution of estimated_revenue_l365d (histogram)
# - Correlation between price × 365 and estimated_revenue_l365d
# - Listings where estimated_revenue_l365d = 0 despite availability
# - Outlier detection: listings with $500K+ annual revenue
# - Compare to AirDNA's estimates for same listings (if available)
```

#### B. Model Testing Layers

| Test Type | What to Test | Ground Truth |
|-----------|-------------|--------------|
| **Train/test evaluation** | MAPE, R², MAE on holdout | InsideAirbnb labels |
| **Cross-validation stability** | Metric variance across folds | InsideAirbnb labels |
| **Sanity checks** | Revenue increases with price, more beds → more revenue | Domain logic |
| **Feature importance** | Price, location, reviews are top drivers | SHAP values |
| **Prediction monotonicity** | Higher nightly_rate → higher predicted revenue | Business rule |
| **Known listing spot checks** | 10 manually researched listings | Manual research |
| **Baseline comparison** | Model beats naive median by borough+beds | Median baseline |

#### C. Sanity Check Tests (CRITICAL — Missing from Plan)
```python
def test_revenue_increases_with_price():
    """If nightly_rate goes up, predicted revenue should go up (all else equal)."""
    base = predict(address="350 5th Ave", bedrooms=2, nightly_rate=200)
    higher = predict(address="350 5th Ave", bedrooms=2, nightly_rate=400)
    assert higher.annual_revenue > base.annual_revenue

def test_revenue_increases_with_bedrooms():
    """More bedrooms should mean more revenue (all else equal)."""
    one_bed = predict(address="350 5th Ave", bedrooms=1, nightly_rate=200)
    three_bed = predict(address="350 5th Ave", bedrooms=3, nightly_rate=200)
    assert three_bed.annual_revenue > one_bed.annual_revenue

def test_revenue_bounded():
    """Revenue should be positive and less than price × 365."""
    result = predict(address="350 5th Ave", bedrooms=2, nightly_rate=200)
    assert 0 < result.annual_revenue < 200 * 365  # Can't exceed 100% occupancy
```

#### D. The Plan's Evaluation Target is Too Loose
MAPE < 40% means the average prediction is off by 40%. For a $45K property, that's ±$18K. **Is that useful to a host making pricing decisions?** The plan should discuss:
- What error margin is acceptable for the end user?
- Should we report revenue as a range (already doing this with confidence) or a point estimate?
- Should we suppress predictions when confidence is low?

---

## 4. How Do We Test the Comp Finder? Edge Cases?

### The Plan Says:
> "Find K nearest listings (K=20). Filter by: same room_type, similar bedrooms (±1), similar accommodates (±2)."

### Missing Test Cases:

#### A. Happy Path
```python
def test_finds_comps_in_manhattan():
    comps = find_comps(lat=40.7484, lng=-73.9857, bedrooms=2, accommodates=4)
    assert len(comps) > 0
    assert all(c.distance_km < 5.0 for c in comps)

def test_comps_sorted_by_distance():
    comps = find_comps(lat=40.7484, lng=-73.9857, bedrooms=2, accommodates=4)
    distances = [c.distance_km for c in comps]
    assert distances == sorted(distances)
```

#### B. Edge Cases — THE BIG ONES

| Scenario | Expected Behavior | Test? |
|----------|-------------------|-------|
| **0 comps found** (rare property type in remote area) | Return error or fallback to model-only prediction | 🔴 Missing |
| **Fewer than K comps found** (only 3 matches) | Use what's available, lower confidence | 🔴 Missing |
| **All comps are far away** (>10km) | Flag low confidence, warn user | 🔴 Missing |
| **Comps have wildly different revenues** (CV > 1.0) | Flag very low confidence | 🔴 Missing |
| **Query at NYC boundary** (e.g., Yonkers, Jersey City) | Should still find NYC comps if within range | 🔴 Missing |
| **bedrooms=0** (studio) | ±1 filter → bedrooms in [0,1]. Does data have studios? | 🔴 Missing |
| **accommodates=1** | ±2 filter → accommodates in [1,3]. Valid? | 🔴 Missing |
| **accommodates=20** (huge property) | Likely 0 comps. Fallback? | 🔴 Missing |
| **Duplicate listings** (same host, same building) | Should be deduped or flagged | 🔴 Missing |

#### C. Scoring Function Tests
```python
def test_bedroom_match_beats_mismatch():
    """A comp with matching bedrooms should score higher than one that doesn't."""
    perfect = score_comp(query_bedrooms=2, comp_bedrooms=2, distance_km=0.5)
    off_by_one = score_comp(query_bedrooms=2, comp_bedrooms=3, distance_km=0.5)
    assert perfect > off_by_one

def test_distance_weight():
    """Closer comp should score higher (all else equal)."""
    close = score_comp(distance_km=0.1, query_bedrooms=2, comp_bedrooms=2)
    far = score_comp(distance_km=2.0, query_bedrooms=2, comp_bedrooms=2)
    assert close > far
```

#### D. Performance Test
```python
def test_comp_finder_under_100ms():
    """With 5000 listings in memory, comp finding should be fast."""
    start = time.time()
    find_comps(lat=40.7484, lng=-73.9857, bedrooms=2, accommodates=4)
    elapsed = time.time() - start
    assert elapsed < 0.1  # 100ms budget
```

---

## 5. What Happens When the Input Address is Outside NYC?

### The Plan Says: **NOTHING.**

### This is a 🔴 Critical Gap.

The model is trained on NYC data only. The comp finder only has NYC listings. But the API accepts any address string. What happens when someone sends:

- `"1600 Pennsylvania Ave, Washington, DC"` (White House)
- `"1 Infinite Loop, Cupertino, CA"` (Apple HQ)
- `"Jersey City, NJ"` (right across the river)
- `"350 5th Ave, New York, NY"` (Empire State Building — in NYC but commercial)

### Required Behavior:

1. **Geocode the address** → get lat/lng
2. **Check if lat/lng is within NYC bounding box** (~40.49°N to 40.92°N, -74.26°W to -73.70°W)
3. **If outside NYC:** Return a clear error: `"Address is outside our NYC coverage area. We currently support New York City only."`
4. **If at boundary:** Still return comps but flag low confidence

### Required Tests:
```python
def test_outside_nyc_returns_error():
    result = estimate(address="1600 Pennsylvania Ave, Washington, DC", ...)
    assert result.error == "outside_coverage_area"
    assert result.status_code == 422

def test_jersey_city_returns_error():
    result = estimate(address="100 Hudson St, Jersey City, NJ", ...)
    assert result.error == "outside_coverage_area"

def test_edge_of_queens_works():
    """Far Rockaway is still NYC."""
    result = estimate(address="Beach 25th St, Far Rockaway, NY", ...)
    assert result.annual_revenue > 0

def test_geocode_failure_returns_error():
    """Address that can't be geocoded."""
    result = estimate(address="asdfghjkl", ...)
    assert result.error == "geocoding_failed"
    assert result.status_code == 422
```

### NYC Bounding Box Validation:
```python
NYC_BOUNDS = {
    "lat_min": 40.49,
    "lat_max": 40.92,
    "lng_min": -74.26,
    "lng_max": -73.70,
}

def is_in_nyc(lat: float, lng: float) -> bool:
    return (NYC_BOUNDS["lat_min"] <= lat <= NYC_BOUNDS["lat_max"] and
            NYC_BOUNDS["lng_min"] <= lng <= NYC_BOUNDS["lng_max"])
```

**Note:** This is a rough rectangle. For production, consider a proper GeoJSON boundary of NYC boroughs. The rectangle includes parts of NJ and Long Island that aren't NYC.

---

## 6. What Happens When bedrooms=0 or bathrooms=0?

### The Plan Says: Nothing explicit. The filter is `bedrooms ± 1`.

### Analysis:

**bedrooms=0 (Studio):**
- The plan filters for `room_type == 'Entire home/apt'`. Studios ARE entire homes with 0 bedrooms.
- InsideAirbnb data likely has studios. The ±1 filter would match bedrooms ∈ [0, 1].
- ✅ Should work, but needs explicit testing.

**bathrooms=0:**
- This is a data quality issue. Can a listing have 0 bathrooms? Possibly shared bath.
- The plan doesn't filter by bathrooms in comp finding, but bathroom match is 15% of the similarity score.
- ⚠️ What does `bathroom_match=0` mean in the scoring function? Division by zero? Need to check.

### Required Tests:
```python
def test_studio_apartment():
    """bedrooms=0 should find studio comps."""
    result = estimate(address="350 5th Ave", bedrooms=0, bathrooms=1, ...)
    assert result.annual_revenue > 0
    assert all(c.bedrooms in [0, 1] for c in result.comps)

def test_zero_bathrooms():
    """bathrooms=0 is unusual but shouldn't crash."""
    result = estimate(address="350 5th Ave", bedrooms=1, bathrooms=0, ...)
    assert result.annual_revenue > 0  # or a clear error

def test_negative_bedrooms():
    """Invalid input should be rejected."""
    result = estimate(address="350 5th Ave", bedrooms=-1, ...)
    assert result.error == "invalid_input"

def test_bedrooms_as_float():
    """What if someone sends bedrooms=1.5?"""
    result = estimate(address="350 5th Ave", bedrooms=1.5, ...)
    # Should either round to 2 or reject
```

### Input Validation Rules (MISSING FROM PLAN):
```python
# The plan has ZERO input validation specification.
# Add:
assert bedrooms >= 0, "bedrooms must be non-negative"
assert bathrooms >= 0, "bathrooms must be non-negative"
assert accommodates >= 1, "accommodates must be at least 1"
assert nightly_rate > 0, "nightly_rate must be positive"
assert isinstance(address, str) and len(address) > 0, "address required"
```

---

## 7. What Happens When nightly_rate is $10 or $10,000?

### The Plan Says: Nothing about input bounds on nightly_rate.

### Analysis:

**nightly_rate=$10:**
- Below any realistic NYC STR price. Model will extrapolate from training data (likely min ~$50).
- Should this be rejected? Or should we return a prediction with a warning?
- The model's `price` feature will be an outlier. XGBoost handles this gracefully (tree-based) but the prediction may be unreliable.

**nightly_rate=$10,000:**
- Ultra-luxury. Training data probably has <10 listings above $1,000/night.
- Model will extrapolate. Prediction will be unreliable.
- The comp finder might find 0 comps in the price range.

### Required Tests:
```python
def test_very_low_price():
    """$10/night should return a warning or be rejected."""
    result = estimate(address="350 5th Ave", nightly_rate=10, ...)
    # Option A: Reject with error
    assert result.error == "nightly_rate_below_minimum"
    # Option B: Accept but flag
    assert result.warnings[0].includes("below typical range")

def test_very_high_price():
    """$10,000/night should work but with low confidence."""
    result = estimate(address="350 5th Ave", nightly_rate=10000, ...)
    assert result.confidence.level == "low"
    assert result.annual_revenue > 0

def test_price_zero():
    """$0/night is invalid."""
    result = estimate(address="350 5th Ave", nightly_rate=0, ...)
    assert result.error == "invalid_input"

def test_price_negative():
    """Negative price is invalid."""
    result = estimate(address="350 5th Ave", nightly_rate=-100, ...)
    assert result.error == "invalid_input"

def test_price_string():
    """Price as string should be rejected."""
    result = estimate(address="350 5th Ave", nightly_rate="two hundred", ...)
    assert result.error == "invalid_input"
```

### Recommended Input Validation:
```python
NIGHTLY_RATE_MIN = 25    # Below this, not a real STR
NIGHTLY_RATE_MAX = 5000  # Above this, model has no training data
NIGHTLY_RATE_TYPICAL_MIN = 50
NIGHTLY_RATE_TYPICAL_MAX = 1000

def validate_nightly_rate(rate):
    if rate < NIGHTLY_RATE_MIN:
        raise ValidationError(f"nightly_rate must be >= ${NIGHTLY_RATE_MIN}")
    if rate > NIGHTLY_RATE_MAX:
        raise ValidationError(f"nightly_rate must be <= ${NIGHTLY_RATE_MAX}")
    if rate < NIGHTLY_RATE_TYPICAL_MIN:
        warn("Below typical NYC range. Prediction may be unreliable.")
    if rate > NIGHTLY_RATE_TYPICAL_MAX:
        warn("Above typical NYC range. Prediction may be unreliable.")
```

---

## 8. How Do We Test the Confidence Interval?

### The Plan Says:
> "Confidence: based on comp revenue variance (CV < 0.25 = high, 0.25-0.50 = medium, > 0.50 = low)"

### Problems:

1. **CV is not a confidence interval.** It's a coefficient of variation. A real confidence interval would be something like "we're 90% confident revenue is between $35K and $55K." The plan conflates these.

2. **The bounds (`revenue_lower`, `revenue_upper`) have no statistical basis described.** How are they computed? Percentiles of comp revenues? Model prediction ± N standard deviations? The plan doesn't say.

3. **The blending (60% XGBoost + 40% comp) makes confidence harder.** The model has its own uncertainty. The comps have their own variance. How do you combine them?

### Required Tests:

```python
def test_confidence_wider_when_fewer_comps():
    """Fewer comps = less certainty = wider interval."""
    many_comps = estimate(address="350 5th Ave", ...)  # 20 comps
    few_comps = estimate(address="some remote area", ...)  # 3 comps
    many_width = many_comps.confidence.revenue_upper - many_comps.confidence.revenue_lower
    few_width = few_comps.confidence.revenue_upper - few_comps.confidence.revenue_lower
    assert few_width > many_width

def test_confidence_contains_prediction():
    """The point estimate should be within the confidence bounds."""
    result = estimate(address="350 5th Ave", ...)
    assert result.confidence.revenue_lower <= result.annual_revenue <= result.confidence.revenue_upper

def test_confidence_symmetric_or_asymmetric():
    """Revenue can't be negative, so lower bound should be >= 0."""
    result = estimate(address="350 5th Ave", ...)
    assert result.confidence.revenue_lower >= 0

def test_confidence_level_classification():
    """CV thresholds should map correctly."""
    # Mock comps with low variance → high confidence
    mock_comps(cv=0.20)
    result = estimate(...)
    assert result.confidence.level == "high"

    # Mock comps with high variance → low confidence
    mock_comps(cv=0.60)
    result = estimate(...)
    assert result.confidence.level == "low"

def test_confidence_realistic_range():
    """Upper bound shouldn't be >3x the prediction."""
    result = estimate(address="350 5th Ave", ...)
    assert result.confidence.revenue_upper < result.annual_revenue * 3
```

### Recommendation:
Define the confidence interval computation explicitly:
```python
# Option A: Percentile-based (simplest)
revenue_lower = np.percentile(comp_revenues, 10)
revenue_upper = np.percentile(comp_revenues, 90)

# Option B: Model + comp combined
# Use quantile regression in XGBoost for model uncertainty
# Combine with comp variance using propagation of uncertainty
```

---

## 9. What Integration Tests Are Needed?

### The Plan Has: Nothing beyond "test_api.py" stub.

### Required Integration Tests:

#### A. Full Pipeline (Happy Path)
```python
def test_full_pipeline_returns_valid_response():
    """End-to-end: API request → geocode → comps → model → response."""
    response = client.post("/v1/rentalizer/estimate", json={
        "address": "350 5th Ave, New York, NY",
        "bedrooms": 2,
        "bathrooms": 1,
        "accommodates": 4,
        "nightly_rate": 200,
        "property_type": "Entire home/apt"
    })
    assert response.status_code == 200
    data = response.json()
    assert "annual_revenue" in data
    assert "confidence" in data
    assert "comps" in data
    assert "market" in data
    assert data["annual_revenue"] > 0
```

#### B. Error Propagation
```python
def test_geocode_failure_propagates_to_api():
    """If geocoding fails, API should return structured error."""
    response = client.post("/v1/rentalizer/estimate", json={
        "address": "asdfghjkl",
        "bedrooms": 2,
        ...
    })
    assert response.status_code == 422
    assert "geocoding_failed" in response.json()["error"]

def test_no_comps_returns_model_only():
    """If comp finder returns 0 results, fall back to model-only."""
    # Use an address in a very sparse area of NYC
    response = client.post("/v1/rentalizer/estimate", json={
        "address": "some sparse area",
        "bedrooms": 5,  # rare
        "accommodates": 16,  # very rare
        ...
    })
    assert response.status_code == 200
    assert response.json()["confidence"]["level"] == "low"
```

#### C. Batch Endpoint
```python
def test_batch_endpoint():
    """Batch should return array of results."""
    response = client.post("/v1/rentalizer/batch", json=[
        {"address": "350 5th Ave, New York, NY", "bedrooms": 2, ...},
        {"address": "1 Main St, Brooklyn, NY", "bedrooms": 1, ...},
    ])
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_batch_partial_failure():
    """If one item in batch fails, others should still succeed."""
    response = client.post("/v1/rentalizer/batch", json=[
        {"address": "350 5th Ave, New York, NY", "bedrooms": 2, ...},
        {"address": "invalid address", "bedrooms": 2, ...},
    ])
    assert response.status_code == 200
    assert response.json()[0]["annual_revenue"] > 0
    assert "error" in response.json()[1]
```

#### D. Response Schema Validation
```python
from jsonschema import validate

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["address", "lat", "lng", "annual_revenue", "monthly_revenue",
                  "confidence", "comps", "market"],
    "properties": {
        "annual_revenue": {"type": "number", "minimum": 0},
        "monthly_revenue": {"type": "array", "items": {"type": "number"}, "minItems": 12, "maxItems": 12},
        "confidence": {
            "type": "object",
            "required": ["level", "revenue_lower", "revenue_upper", "cv"],
            "properties": {
                "level": {"enum": ["high", "medium", "low"]},
                "cv": {"type": "number", "minimum": 0},
            }
        },
    }
}

def test_response_matches_schema():
    response = client.post("/v1/rentalizer/estimate", json=valid_input)
    validate(instance=response.json(), schema=RESPONSE_SCHEMA)
```

---

## 10. What's the Minimum Test Coverage Target?

### The Plan Says: Nothing about coverage.

### Recommendation:

| Module | Minimum Line Coverage | Minimum Branch Coverage |
|--------|----------------------|------------------------|
| `geocoder.py` | 95% | 90% |
| `comp_finder.py` | 90% | 85% |
| `prepare_data.py` | 85% | 80% |
| `train_model.py` | 80% | 75% |
| `api.py` | 90% | 85% |
| **Overall** | **85%** | **80%** |

### CI Configuration:
```yaml
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=html --cov-report=term --cov-fail-under=85"
```

### What NOT to Count:
- Model training code (run once, not in production path)
- Data download scripts
- Jupyter notebooks

---

## 11. How Do We Detect Model Drift Over Time?

### The Plan Says:
> "Temporal drift — InsideAirbnb data is quarterly. Market conditions change."

But provides **no mitigation strategy or monitoring plan**.

### Required Drift Detection:

#### A. Input Distribution Monitoring
```python
# Track distribution of incoming requests
# Alert if:
# - Average nightly_rate shifts >20% from training distribution
# - Borough distribution shifts (suddenly 80% Brooklyn queries)
# - Bedroom distribution shifts
# - New property types appear that weren't in training data
```

#### B. Prediction Distribution Monitoring
```python
# Track distribution of predictions over time
# Alert if:
# - Mean predicted revenue drops >15% (market crash? model degradation?)
# - Prediction variance suddenly increases
# - Confidence levels skew heavily toward "low"
# - Predictions cluster suspiciously (model collapsing to mean)
```

#### C. Ground Truth Comparison (When Available)
```python
# If new InsideAirbnb data is released quarterly:
# 1. Load new estimated_revenue_l365d
# 2. Run model predictions on new listings
# 3. Compare MAPE, R² to baseline
# 4. Alert if MAPE > baseline + 10%
# 5. Retrain if degradation confirmed
```

#### D. Automated Retraining Pipeline
```python
# Trigger conditions:
# - New InsideAirbnb data available (quarterly check)
# - MAPE degradation > 10% from baseline
# - Manual trigger

# Retraining process:
# 1. Download new data
# 2. Re-run data preparation
# 3. Retrain model
# 4. Evaluate on holdout
# 5. Compare to current production model
# 6. Deploy only if new model is better
# 7. A/B test if uncertain
```

---

## 12. What Monitoring/Alerting is Needed in Production?

### The Plan Says: Nothing.

### Required Production Monitoring:

#### A. API Health
| Metric | Alert Threshold |
|--------|----------------|
| Request latency (p50) | > 500ms |
| Request latency (p99) | > 3s |
| Error rate | > 1% of requests |
| Geocoder failure rate | > 5% |
| Comp finder returning 0 comps | > 10% of requests |
| 429 rate limits from Nominatim | > 0 (implement backoff) |

#### B. Model Quality
| Metric | Alert Threshold |
|--------|----------------|
| Prediction mean (rolling 7d) | Shift > 15% from baseline |
| Low confidence rate | > 30% of requests |
| Prediction = 0 | Any occurrence |
| Prediction > $500K | Any occurrence (likely error) |
| Comp count per request (avg) | < 5 (sparse data) |

#### C. Infrastructure
| Metric | Alert Threshold |
|--------|----------------|
| Memory usage (model in-memory) | > 80% of available |
| CPU utilization | > 80% sustained |
| Disk usage (caches, logs) | > 90% |
| Process restarts | > 0 in 1 hour |

#### D. Logging Requirements
```python
# Every request should log:
# - Request ID (for tracing)
# - Input: address, bedrooms, bathrooms, accommodates, nightly_rate
# - Geocoded lat/lng
# - Number of comps found
# - Prediction: annual_revenue, confidence level
# - Latency breakdown: geocode_ms, comp_ms, model_ms, total_ms
# - Warnings (out of range inputs, low confidence, etc.)

# Do NOT log:
# - Full comp listing details (PII risk)
# - Raw API keys or tokens
```

---

## Summary of Critical Missing Items

### 🔴 Must-Have Before Launch:
1. **Input validation** — Zero validation exists in the plan. Add schema validation for all inputs.
2. **NYC boundary check** — No handling for out-of-coverage addresses.
3. **Error handling** — No specification for geocoder failure, 0 comps, invalid input.
4. **Geocoder mocking strategy** — Can't test without this.
5. **Comp finder edge cases** — 0 comps, boundary addresses, extreme inputs.
6. **Response schema validation** — No contract testing.
7. **Sanity check tests** — Revenue monotonicity, bounds, basic invariants.

### 🟡 Should-Have Before Launch:
8. **Confidence interval methodology** — Currently underspecified.
9. **Monitoring/alerting** — Zero production observability.
10. **Drift detection** — Acknowledged as risk but no mitigation.
11. **Test coverage target** — No coverage requirement.
12. **Performance benchmarks** — No latency targets.

### 🟢 Nice-to-Have:
13. **Load testing** — Single-server MVP doesn't need this yet.
14. **A/B testing framework** — For model upgrades.
15. **Canary deployments** — For safe model rollouts.

---

## Final Verdict

**The plan is a 7/10 as a data science plan and a 3/10 as an engineering plan.**

The model training, evaluation, and feature engineering are well-thought-out. But the testing strategy is essentially "we'll have two test files." That's not a strategy — it's a directory structure.

**Recommendation:** Before writing any code, spend 2 hours adding the following to the plan:
1. Input validation specification (all fields, all bounds)
2. Error handling specification (every failure mode → every response)
3. Test case list (minimum 150 cases organized by module)
4. Monitoring metric list (minimum 10 metrics with alert thresholds)
5. Confidence interval computation formula (make it precise, not "CV-based")

The code will be better for it.
