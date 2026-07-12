---
name: Rentalizer estimator architecture (hybrid, coverage-driven)
description: How the revenue estimator decides which engine to use and how coverage is defined
---

## Rule
The `/v1/estimate` endpoint is a **hybrid** routed by geography, and coverage is
**data-driven, not region-hardcoded**:
- **NYC** (address inside the NYC bounding box) → the trained LightGBM model +
  NYC comp index (train.csv). NYC data is NOT in the map/listings DB, so the ML
  model is the only source for it. Reported `model_version` = the model's meta version.
- **Everywhere else** → comp-based estimate over the shared listings SQLite DB
  (`db/airbnb.db`) using real `estimated_revenue_l365d`. Reported `model_version` = `comps-1.0`.
- **Coverage** = "are there ≥ MIN_COMPS comparable listings within MAX_RADIUS_KM of
  the geocoded point?" If not → raise `OutsideCoverageError` with a message listing
  the DB's distinct states. There is NO hardcoded CA/FL list anywhere in the routing.

**Why:** The user explicitly wanted the estimator to stop being NYC-only and to
"work for all cities and states" as data is added. Making coverage depend on DB
data density means loading a new city/state into the `listings` table makes it work
with zero code changes. The estimator and the map now share one data source, which
fixes the original "two disconnected products" problem.

## How to apply
- To add a market: load its listings (with `estimated_revenue_l365d`, lat/lng,
  room_type, snapshot_date) into the `listings` table. No estimator code change needed.
- Do NOT reintroduce hardcoded region checks for the comp path; keep coverage a
  function of comp density (see `src/market_estimator.py` constants).
- The comp path returns real per-market `data_freshness` (MAX snapshot_date for that
  city); the NYC/ML path still uses the config `DATA_FRESHNESS` string.
- The response `market.borough` field is reused as a generic area label (NYC borough
  or "City, ST"); the frontend labels it "Area".
