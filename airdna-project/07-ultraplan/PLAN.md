# ULTRAPLAN: Rentalizer Clone — Revenue Prediction Engine

## Problem Statement
Build a revenue estimation tool for short-term rental properties. Given an address and property characteristics, predict annual revenue with confidence intervals.

## Key Insight (from data analysis)
InsideAirbnb provides pre-computed revenue estimates for 21,515+ NYC listings. Calendar-based booking detection is unreliable (0.54 correlation). Review-based estimation fails due to unknown review rates. The correct approach is supervised learning on InsideAirbnb's labeled data.

## Architecture

```
User Input (address, beds, baths, guests, price)
        │
        ▼
┌─────────────────────┐
│   GEOCODING (Nominatim)  │
│   address → lat/lng      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────┐
│   COMP FINDER (PostGIS)  │
│   Find N nearest similar │
│   listings from IA data  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────┐
│   FEATURE ENGINEERING    │
│   Comp stats, distance,  │
│   similarity scores      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────┐
│   REVENUE PREDICTOR      │
│   XGBoost model trained  │
│   on IA labeled data     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────┐
│   CONFIDENCE INTERVAL    │
│   From comp variance +   │
│   model uncertainty      │
└──────────┬──────────────┘
           │
           ▼
   JSON Response: {revenue, confidence, comps}
```

## Phase 1: Data Preparation (Day 1)

### 1.1 Clean InsideAirbnb Data
- Load listings.csv.gz (30,259 NYC listings)
- Filter: room_type == 'Entire home/apt'
- Filter: has_availability == TRUE
- Filter: estimated_revenue_l365d > 0 (21,515 labeled)
- Filter: minimum_nights <= 30 (short-term only → ~5,593 listings)
- Remove outliers: revenue > 99th percentile or < 1st percentile
- Result: ~5,000 labeled STR listings

### 1.2 Feature Engineering
Numeric features:
- `price` (nightly rate)
- `accommodates` (guest capacity)
- `bedrooms`, `bathrooms`, `beds`
- `minimum_nights`
- `number_of_reviews`, `number_of_reviews_ltm`, `reviews_per_month`
- `availability_30`, `availability_60`, `availability_90`, `availability_365`
- `review_scores_rating` (1-5)
- `host_listings_count` (professional host indicator)
- `latitude`, `longitude`

Categorical features:
- `neighbourhood_group_cleansed` (borough)
- `property_type` (Apartment, House, etc.)
- `instant_bookable` (t/f)
- `host_is_superhost` (t/f)

Derived features:
- `price_per_person` = price / accommodates
- `review_velocity` = number_of_reviews_ltm / 12 (reviews per month)
- `host_experience_months` = months since host_since
- `listing_age_months` = months since first_review
- `occupancy_proxy` = (365 - availability_365) / 365

### 1.3 Train/Test Split
- 80/20 split, stratified by borough
- Save as `train.csv` and `test.csv`

## Phase 2: Model Training (Day 1-2)

### 2.1 Baseline Model
- Simple median revenue by (borough, bedrooms) as baseline
- Measure MAE, MAPE, R² on test set

### 2.2 XGBoost Model
- Train on all features
- Hyperparameters: max_depth=6, n_estimators=500, learning_rate=0.05
- 5-fold cross-validation
- Target: `log(estimated_revenue_l365d)` (log-transform for better distribution)

### 2.3 Evaluation Metrics
- **MAE** (Mean Absolute Error): dollar amount of average error
- **MAPE** (Mean Absolute Percentage Error): percentage error
- **R²**: variance explained
- **Within 25%**: % of predictions within 25% of actual
- **Within 50%**: % of predictions within 50% of actual
- Target: MAPE < 40%, Within 50% > 60%

### 2.4 Feature Importance
- SHAP values for interpretability
- Identify top 10 most predictive features
- Validate that price, location, reviews are top drivers

## Phase 3: Comp-Based Estimation (Day 2)

### 3.1 Geocoding
- Use Nominatim (free, no API key)
- Cache geocoding results
- Fallback: Mapbox if Nominatim fails

### 3.2 Comp Finding
- Load all labeled listings into memory
- For each query: find K nearest listings (K=20)
- Filter by: same room_type, similar bedrooms (±1), similar accommodates (±2)
- Score by: distance (40%), bedroom match (25%), bathroom match (15%), capacity match (15%), property type match (5%)

### 3.3 Comp-Based Prediction
- Weighted average of comp revenues (weighted by similarity score)
- Also run XGBoost prediction
- Final estimate: 60% XGBoost + 40% comp-based
- Confidence: based on comp revenue variance (CV < 0.25 = high, 0.25-0.50 = medium, > 0.50 = low)

## Phase 4: API (Day 2-3)

### 4.1 FastAPI Endpoint
```
POST /v1/rentalizer/estimate
{
  "address": "350 5th Ave, New York, NY",
  "bedrooms": 2,
  "bathrooms": 1,
  "accommodates": 4,
  "nightly_rate": 200,
  "property_type": "Entire home/apt"
}

Response:
{
  "address": "350 5th Ave, New York, NY",
  "lat": 40.7484,
  "lng": -73.9857,
  "annual_revenue": 45000,
  "monthly_revenue": [3200, 3100, 3800, 4200, 4800, 5200, 5500, 5400, 4900, 4100, 3500, 3300],
  "confidence": {
    "level": "medium",
    "revenue_lower": 35000,
    "revenue_upper": 55000,
    "cv": 0.32
  },
  "comps": [
    {"id": 123, "title": "2BR near Times Square", "distance_km": 0.3, "revenue": 48000, "similarity": 0.92},
    ...
  ],
  "market": {
    "borough": "Manhattan",
    "median_revenue": 42000,
    "median_price": 250,
    "active_listings": 2787
  }
}
```

### 4.2 Batch Endpoint
```
POST /v1/rentalizer/batch
[{address, bedrooms, bathrooms, accommodates, nightly_rate, property_type}, ...]
```

## Phase 5: Validation (Day 3)

### 5.1 Cross-Validation
- 5-fold CV on training data
- Report mean ± std of all metrics

### 5.2 Holdout Test
- Final evaluation on test set (never seen during training)
- Compare to baseline (median by borough+bedrooms)

### 5.3 Real-World Test
- Pick 10 real NYC listings
- Compare our estimates to AirDNA's Rentalizer (if accessible)
- Compare to InsideAirbnb's estimates

## File Structure
```
airdna-project/
├── 07-ultraplan/
│   └── PLAN.md (this file)
├── 08-rentalizer/
│   ├── data/
│   │   ├── train.csv
│   │   └── test.csv
│   ├── models/
│   │   ├── revenue_model.pkl
│   │   └── feature_importance.json
│   ├── src/
│   │   ├── prepare_data.py
│   │   ├── train_model.py
│   │   ├── comp_finder.py
│   │   ├── geocoder.py
│   │   └── api.py
│   ├── tests/
│   │   ├── test_model.py
│   │   └── test_api.py
│   └── requirements.txt
```

## Success Criteria
| Metric | Baseline (median) | Target | Stretch |
|--------|-------------------|--------|---------|
| MAPE | 80%+ | <40% | <30% |
| Within 50% | 30%+ | >60% | >70% |
| R² | 0.3+ | >0.7 | >0.8 |
| MAE | $30K+ | <$15K | <$10K |

## Risks
1. **Small dataset** — Only ~5,000 labeled STR listings in NYC. May overfit.
2. **City-specific** — Model trained on NYC won't generalize to other cities without retraining.
3. **Temporal drift** — InsideAirbnb data is quarterly. Market conditions change.
4. **No scraping** — Can't get real-time data without building a scraper (deferred).
5. **Feature leakage** — `availability_365` is partially a function of revenue. Need to be careful.

## What's NOT in scope (deferred)
- ❌ Calendar-based booking detection (proven unreliable)
- ❌ Review-based revenue estimation (proven unreliable)
- ❌ Cross-platform matching (Vrbo blocked, Booking.com partial)
- ❌ Dynamic pricing (depends on accurate revenue first)
- ❌ Real-time scraping (quarterly InsideAirbnb data sufficient for MVP)
- ❌ Multi-city support (NYC only for MVP)
