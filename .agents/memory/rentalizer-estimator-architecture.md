---
name: Rentalizer estimator architecture
description: Hybrid estimator routing and how each path's data can/can't go stale without a restart
---

Hybrid routing in `src/api.py`: NYC addresses (`in_nyc_bounds`) use a trained ML model + `comp_finder.py`'s KD-tree; every other market uses `market_estimator.estimate_from_db()`, a pure per-request SQL query against the shared `db/airbnb.db` `listings` table (no caching, so it's always fresh — no staleness concern there).

`comp_finder.py`'s NYC comp index/market stats are built once from a **static** `data/train.csv` (engineered from a one-time InsideAirbnb export), which is a completely different pipeline from the growing `listings` table other markets use — it has no `snapshot_date` column and nothing currently regenerates it at runtime. Its freshness signal is therefore the CSV's file mtime, not a DB snapshot: `comp_finder._ensure_fresh()` stats the file cheaply on every `find_comps()`/`get_market_stats()` call and only reloads+rebuilds the KD-tree when the mtime has changed, mirroring `amenity_calibration.get_calibration()`'s cheap-check/expensive-rebuild pattern but keyed on file mtime since no DB snapshot exists for this path.

**Why:** avoids requiring a process restart to pick up either a new market snapshot (comp/amenity paths) or a refreshed NYC training CSV, while keeping the common case (nothing changed) a single cheap check.
