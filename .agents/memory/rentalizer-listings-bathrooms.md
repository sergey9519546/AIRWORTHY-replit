---
name: Rentalizer listings bathrooms column
description: The map listings table lacked a bathrooms column; how it was added/backfilled without wiping demand_curve
---

# Listings bathrooms column

The map DB (`db/airbnb.db`, `listings` table) originally had **no** bathrooms
column, despite briefs/tasks assuming one existed. Bedrooms/accommodates were
present; bathrooms was simply never ingested.

**Source of truth:** InsideAirbnb raw `listings.csv.gz` carries both a numeric
`bathrooms` column (frequently blank, ~79% populated) and a free-text
`bathrooms_text` (e.g. "1.5 baths", "1 shared bath", "Half-bath", ~98%
populated). Prefer parsing the leading number out of `bathrooms_text`, fall back
to the numeric column. `parse_bathrooms()` in `scripts/load_data.py` does this.

**Backfill without data loss:** `listings.demand_curve` is populated by a
separate script (load_demand_curves), so you must NOT drop/reload the listings
table to add a column. Use an in-place `ALTER TABLE ADD COLUMN` + per-row UPDATE
matched by `(id, state, city, snapshot_date)` from the cached raw files. See
`scripts/add_bathrooms_column.py` (idempotent).

**Why:** wiping and reloading listings via load_map_data would erase the
demand_curve values that other features depend on.
