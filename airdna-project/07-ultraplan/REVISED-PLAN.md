# REVISED ULTRAPLAN: Rentalizer Clone v2

> Incorporates all 5 audit findings. Changes from v1 marked with [v2].

---

## What Changed (Summary)

| Audit | Critical Issues | Changes Made |
|-------|----------------|--------------|
| **Data Science** | Arbitrary blend, no tuning, price leakage | Optimize α via CV, Optuna tuning, investigate leakage |
| **Engineering** | Nominatim unreliable, no error handling, no caching | Mapbox primary, error hierarchy, TTLCache |
| **Product** | No user, NYC bad for STR, API-first wrong | Target user defined, consider other markets, build UI first |
| **Legal** | Zero attribution, no disclaimers, PII exposure | Add attribution, disclaimers, strip PII |
| **Testing** | Zero tests, no validation, no monitoring | 150+ test cases, input validation, drift detection |

---

## Target User [v2]

**"Investor evaluating a short-term rental property"** — has a specific address, wants to know annual revenue, needs confidence range. Price-sensitive, won't pay AirDNA $120/mo for a one-time lookup.

**NOT targeting:** developers (API), property managers (batch), real estate agents (PDF reports). These are later.

**Market decision:** Start with NYC (data available), but evaluate expanding to Nashville/Scottsdale/Gulf Shores (STR-friendly regulations). NYC's Local Law 18 makes it a legally complex market for hosts.

---

## Architecture [v2]

```
User enters address in web form
        │
        ▼
┌─────────────────────────┐
│ INPUT VALIDATION         │
│ - Address non-empty      │
│ - Bedrooms 0-10          │
│ - Bathrooms 0-10         │
│ - Accommodates 1-20      │
│ - Nightly rate $25-$5000 │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ GEOCODING (Mapbox primary)│
│ - Nominatim fallback     │
│ - NYC bounds check       │
│ - Cache 7 days           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ COMP FINDER (KD-Tree)    │
│ - K=20 nearest           │
│ - Filter: room_type,     │
│   bedrooms ±1, capacity  │
│ - Score: distance+match  │
│ - Handle 0 comps → fallback│
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ FEATURE ENGINEERING      │
│ - 15-20 features (after  │
│   selection)             │
│ - No price in model      │
│   (use in comp path only)│
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ REVENUE PREDICTION       │
│ - XGBoost (Optuna-tuned) │
│ - LightGBM baseline      │
│ - Blend α optimized via  │
│   CV, not hardcoded      │
│ - Log-transform + smearing│
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ CONFIDENCE INTERVAL      │
│ - Percentile-based from  │
│   comp revenues (10th/   │
│   90th)                  │
│ - Widen when fewer comps │
│ - Validate coverage      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ RESPONSE + DISCLAIMERS   │
│ - Revenue range (not     │
│   point estimate)        │
│ - CC BY 4.0 attribution  │
│ - Legal disclaimer       │
│ - No listing titles      │
│ - No host PII            │
└─────────────────────────┘
```

## Phases [v2]

### Phase 0: Legal & Data Prep (Day 0) [NEW]
- Strip all host PII from dataset (names, locations, bios)
- Remove copyrighted content (listing titles, descriptions)
- Add CC BY 4.0 attribution to all surfaces
- Draft disclaimers for revenue estimates
- Cache InsideAirbnb datasets locally (CC BY 4.0 is perpetual once downloaded)
- Document data provenance chain

### Phase 1: Data Preparation (Day 1)
- Load InsideAirbnb NYC data (30,259 listings)
- Filter: entire home, has_availability, min_nights <= 30, revenue > 0
- Result: ~5,000 labeled STR listings
- Feature engineering (15-20 features after selection)
- **[v2] Investigate price leakage:** check if model just learns revenue ≈ price × factor
- **[v2] Add features:** review_recency, subway_distance, host_response_rate
- **[v2] Remove:** monthly_revenue from API (no monthly training data)
- Train/test split: 80/20, stratified by borough AND revenue tier

### Phase 2: Model Training (Day 1-2)
- **[v2] Baselines:** median by borough+bedrooms, Ridge regression, k-NN comp-based
- Train XGBoost + LightGBM + CatBoost, pick best on CV
- **[v2] Hyperparameter tuning:** Optuna (max_depth, learning_rate, n_estimators, min_child_weight, subsample, colsample_bytree, reg_alpha, reg_lambda)
- **[v2] Early stopping:** eval_set with early_stopping_rounds=50
- **[v2] Log-transform:** Duan's smearing correction for unbiased back-transform
- **[v2] Blend optimization:** grid search α ∈ [0, 0.1, ..., 1.0] via CV, or Ridge meta-learner
- **[v2] Feature selection:** correlation filter → SHAP-based selection → aim for 10-15 features
- Evaluate: MAPE, MdAPE, R², MAE, Within 25%/50%, stratified by borough and revenue tier

### Phase 3: Comp-Based Estimation (Day 2)
- Geocoding: Mapbox primary (100K free/mo), Nominatim fallback
- **[v2] Cache geocoding 7 days** with normalized address keys
- Comp finding: KD-Tree in memory (5K listings), filter by room_type/bedrooms/capacity
- **[v2] Handle edge cases:** 0 comps → model-only with low confidence; >10km comps → warn
- Confidence: percentile-based (10th/90th of comp revenues), validate coverage

### Phase 4: UI + API (Day 2-3) [v2: Build UI first]
- **[v2] Single-page web app** (React or plain HTML): one input field, one output card
- **[v2] API secondary:** only if users ask for it
- Response includes: revenue range, confidence level, top 5 comps (anonymized), market stats
- **[v2] Disclaimers in every response** and on every UI surface
- **[v2] Attribution in footer/credits page**

### Phase 5: Testing (Day 3) [v2: Much more rigorous]
- 150+ test cases (unit, integration, edge cases, contract)
- Input validation for all fields
- NYC boundary check
- Geocoder mock fixtures (50+ addresses)
- Sanity checks: revenue monotonicity, bounds, confidence containment
- Performance: <100ms comp finding, <500ms total (cached)

### Phase 6: Validation (Day 3)
- Cross-validation: 5-fold, report mean ± std
- Holdout test: final evaluation
- **[v2] Sanity test:** 10 manually researched NYC listings
- **[v2] AirDNA comparison:** internal only, never published

---

## Success Criteria [v2]

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| MAPE | 80%+ | <40% | <30% |
| MdAPE | 60%+ | <30% | <20% |
| Within 50% | 30%+ | >60% | >70% |
| R² | 0.3+ | >0.7 | >0.8 |
| MAE | $30K+ | <$15K | <$10K |
| CI coverage (90%) | N/A | 85-95% | 88-92% |
| Test cases | 0 | 150+ | 200+ |
| Test coverage | 0% | >85% | >90% |

---

## Legal Must-Dos (Before Launch) [NEW]

1. CC BY 4.0 attribution on all surfaces
2. Comprehensive disclaimers (not financial advice, estimates only)
3. Strip all host PII from dataset
4. Remove copyrighted content from API responses
5. Draft Terms of Service with limitation of liability
6. Draft Privacy Policy

---

## Risks [v2]

| Risk | Mitigation |
|------|------------|
| Price leakage | Validate model beats naive price×factor baseline |
| Overfitting (5K samples) | Optuna tuning, early stopping, regularization |
| NYC Local Law 18 | Position as market analysis, not investment advice |
| InsideAirbnb shutdown | Cache data locally, build source-agnostic pipeline |
| Model accuracy insufficient | Benchmark against AirDNA internally first |
| Legal exposure | Attribution, disclaimers, PII stripping, ToS |
| Single-source dependency | Architecture supports swapping data sources |

---

## What's NOT in Scope [v2]

- ❌ Calendar-based booking detection (proven unreliable)
- ❌ Review-based revenue estimation (proven unreliable)
- ❌ Cross-platform matching (Vrbo blocked)
- ❌ Dynamic pricing (depends on accurate revenue first)
- ❌ Real-time scraping (quarterly data sufficient for MVP)
- ❌ Multi-city (NYC first, expand after validation)
- ❌ API-first (UI first, API later)
- ❌ Monthly revenue breakdown (no monthly training data)
- ❌ Batch endpoint (no demand on day 1)
- ❌ PostgreSQL/PostGIS (in-memory sufficient for 5K listings)

---

## File Structure [v2]

```
airdna-project/08-rentalizer/
├── src/
│   ├── __init__.py
│   ├── config.py              # Settings, paths, constants
│   ├── schemas.py             # Pydantic request/response models
│   ├── exceptions.py          # Custom exception classes
│   ├── geocoder.py            # Mapbox + Nominatim + cache
│   ├── comp_finder.py         # KD-Tree based comp search
│   ├── features.py            # Feature engineering pipeline
│   ├── model.py               # Model loading, prediction
│   ├── confidence.py          # CI computation
│   ├── validation.py          # Input validation + NYC bounds
│   └── api.py                 # FastAPI app (secondary)
├── data/
│   ├── train.csv
│   ├── test.csv
│   └── geocode_cache.json
├── models/
│   ├── revenue_model.pkl
│   └── feature_importance.json
├── tests/
│   ├── unit/                  # 80+ tests
│   ├── integration/           # 30+ tests
│   ├── edge_cases/            # 40+ tests
│   └── conftest.py            # Fixtures, mocks
├── templates/
│   └── index.html             # Single-page web app
├── static/
│   └── style.css
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── README.md                  # With CC BY 4.0 attribution
```
