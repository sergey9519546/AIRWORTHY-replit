# Session Resume — AirDNA Clone Project
> **Last Updated:** 2026-06-29 08:51 UTC
> **Status:** MVP built, model trained, API running, 10 premortem fixes applied

---

## What This Project Is

Building an AirDNA competitor — a short-term rental revenue estimation tool. Given an address + property details, predict annual Airbnb revenue for NYC properties.

## Current State

### Working
- ✅ FastAPI backend on port 8000 (6 endpoints)
- ✅ LightGBM model v3.0.0 (52 features, R²=0.563, MdAPE=23.3%)
- ✅ KD-Tree comp finder (4,089 listings indexed)
- ✅ Geocoding (Mapbox + Nominatim, thread-safe, 7-day cache)
- ✅ Conformal prediction confidence intervals (80% CI coverage = 80.1%)
- ✅ XSS-safe frontend with Leaflet map
- ✅ Legal compliance (CC BY 4.0 attribution, disclaimers)
- ✅ 10 premortem fixes applied

### Not Done
- ❌ Tests (0 written, 123 planned)
- ❌ Authentication (API key auth defined but not enforced in dev mode)
- ❌ Rate limiting (slowapi imported, configured at 30/min)
- ❌ Deployment (Dockerfile exists, not deployed)
- ❌ Multi-city (NYC only)
- ❌ Real-time data (quarterly InsideAirbnb snapshots)

---

## Project Structure

```
airdna-project/
├── 00-index/                    # Master index + session exports
├── 01-airdna-research/          # 14 files — AirDNA company/tech/algorithms
├── 02-airbnb-api/               # 9 files — Cracked APIs (Airbnb + Booking.com)
├── 03-tools-and-methods/        # 4 files — Scraping tools, anti-bot
├── 04-clone-blueprint/          # 14 files — Full blueprint docs
├── 05-data-samples/             # 7 files — Real API responses
├── 06-insideairbnb-data/        # 154MB — NYC listings + calendar + reviews
├── 07-ultraplan/                # Plans, audits, innovations
│   ├── FINAL-PLAN.md            # 23-task build plan
│   ├── FIX-PLAN.md              # 16 fixes
│   ├── PREMORTEM.md             # 10 silent failures
│   ├── TOOLS-AND-PLUGINS.md     # Available tools
│   ├── REVISED-PLAN.md          # Post-audit revision
│   └── audit-*.md               # 5 subagent reviews
├── 08-rentalizer/               # THE APPLICATION
│   ├── src/                     # 11 Python modules
│   ├── scripts/                 # 4 data/training scripts
│   ├── templates/               # HTML
│   ├── static/                  # CSS + JS
│   ├── data/                    # train.csv, test.csv, mta_stations.csv
│   ├── models/                  # revenue_model.pkl, meta.json, calibration.json
│   ├── tests/                   # Empty (needs writing)
│   ├── PREMORTEM-AUDIT.md       # 23KB formal audit
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── memory/                      # Daily notes
│   └── 2026-06-29.md            # Today's session log
├── AGENTS.md                    # Agent behavior rules
├── SOUL.md                      # Persona/tone
├── USER.md                      # User info
├── TOOLS.md                     # Local tool notes
├── IDENTITY.md                  # Agent identity
├── HEARTBEAT.md                 # Heartbeat config
└── MEMORY.md                    # Long-term memory (not created yet)
```

---

## Key Technical Decisions

1. **LightGBM over XGBoost** — Better MAPE (58.5% vs 61.7%)
2. **STR-only data** — Filtered min_nights < 30 (was 72% LTR mixed in)
3. **Non-leaky features** — Removed reviews, availability, review_score
4. **Smart blend** — Dynamic α (0.3-0.7) based on model vs comp ratio
5. **Conformal prediction** — Calibrated CIs, not arbitrary multipliers
6. **InsideAirbnb as data source** — Free, CC BY 4.0, quarterly updates
7. **GeoJSON borough detection** — Polygon lookup, not bounding boxes

---

## Model Performance (Final)

| Metric | Value |
|--------|-------|
| Algorithm | LightGBM v3.0.0 |
| Features | 52 |
| R² | 0.563 |
| MAPE | 58.5% |
| MdAPE | 23.3% |
| Within 25% | 52.6% |
| Within 50% | 78.0% |
| 80% CI coverage | 80.1% |
| Training data | 1,164 NYC STR listings |

### Top 5 Features
1. price_num (874 importance)
2. price_per_person (727)
3. num_amenities (563)
4. nearest_landmark_km (443)
5. longitude (381)

---

## API Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/` | GET | Web UI |
| `/v1/estimate` | POST | Revenue estimate (30/min rate limit) |
| `/v1/batch` | POST | Batch estimates (max 20, 5/min) |
| `/v1/health` | GET | Health check |
| `/v1/ready` | GET | Readiness probe |
| `/v1/model/info` | GET | Model metadata |
| `/v1/credits` | GET | CC BY 4.0 attribution |

---

## Premortem Audit Findings (Top 5 Fixed)

1. ✅ Property type columns aligned to training data
2. ✅ Transit features removed (were in training but not inference)
3. ✅ min_nights/superhost/host_listings as user inputs
4. ✅ Blend fallback uses market median when 0 comps
5. ✅ Confidence intervals calibrated with conformal prediction

---

## What To Do Next

### Immediate (P0)
1. Write tests (123 planned in PREMORTEM-AUDIT.md)
2. Add authentication enforcement
3. Deploy to Railway or Fly.io

### Short-term (P1)
4. Add more data sources (holidays, events, demographics)
5. Validate on real NYC listings (compare to AirDNA)
6. Add multi-city support

### Long-term (P2)
7. Chrome extension (see revenue on Airbnb pages)
8. PDF reports
9. API marketplace

---

## Key Files to Read First

1. `08-rentalizer/PREMORTEM-AUDIT.md` — Latest audit, most current findings
2. `08-rentalizer/src/api.py` — Main application logic
3. `08-rentalizer/src/model.py` — Model loading and prediction
4. `08-rentalizer/src/comp_finder.py` — Comparable listing finder
5. `08-rentalizer/scripts/prepare_data.py` — Data pipeline
6. `07-ultraplan/FINAL-PLAN.md` — Original build plan
7. `memory/2026-06-29.md` — Today's session log

---

## Skills & Tools Available

### OpenClaw Skills (45 installed)
- agent-browser (v0.27.0) — Browser automation
- data-analysis — Statistical analysis
- code-generator — Code scaffolding
- github — Version control
- clawhub-cli — Install more skills
- + 40 others

### Python Packages (installed)
- xgboost, lightgbm, optuna, shap, scikit-learn
- fastapi, uvicorn, pydantic
- pandas, numpy, scipy, matplotlib
- geopy, cachetools, pytest
- requests, playwright

---

## How to Start the Server

```bash
cd airdna-project/08-rentalizer
python3 -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## How to Retrain the Model

```bash
cd airdna-project/08-rentalizer
python3 scripts/prepare_data.py
python3 scripts/add_enhanced_features.py
python3 scripts/train_model.py 50
```

## How to Run Tests

```bash
cd airdna-project/08-rentalizer
pytest tests/ -v
```
