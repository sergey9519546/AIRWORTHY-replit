---
name: Amenity revenue calibration
description: How amenity revenue-impact percentages are derived from real listing data vs. the fixed heuristic fallback, and how the cache stays fresh
---

Amenity impact percentages (pool, hot tub, parking, EV charger, gym, pet-friendly, workspace) are calibrated from `listings.amenities` free-text vs. `estimated_revenue_l365d`, comparing with/without averages **within the same state and bedroom-count bucket** (to control for the "bigger homes have more amenities and more revenue" confound). Coverage is state-level only (`db/airbnb.db` currently has ca/fl) because that's the coarsest grain with enough listings on both sides of the comparison to trust.

**Why:** A global fixed percentage (e.g. "pool = +6%") was a disclosed guess; real per-market data was already sitting in the InsideAirbnb `amenities` column and unused for this purpose.

**How to apply:** `amenity_calibration.lookup(state, amenity_key)` returns a calibrated entry only when both sides of the comparison meet a minimum sample size; otherwise callers (`enrichment.amenity_multiplier`/`amenity_drivers`) fall back to the fixed heuristic in `enrichment.AMENITIES` and disclose it as a rough (non-data-backed) estimate via `is_data_backed: false`. The calibration cache is keyed by the newest `snapshot_date` in `listings` (same freshness signal `/api/cities` exposes) — a cheap `MAX(snapshot_date)` check runs on every call, and the full-table recompute only fires when that value changes, so newly loaded market data (via `scripts/load_data.py`) is picked up without a server restart.
