---
name: Rentalizer seasonal demand curves
description: How the map's Demand layer gets a real month-by-month signal despite empty calendar/reviews tables.
---

## The data reality (non-obvious)
- `db/airbnb.db` `calendar` and `reviews` tables are **empty** (0 rows) — the ETL
  (`scripts/load_map_data.py`) deliberately loads only the latest listings
  snapshot per city for speed. So there is NO day-level or review-date data in the DB.
- All `listings` snapshots fall in a single ~2-week June 2026 window, so there is
  no historical time series per listing either.
- InsideAirbnb `calendar.csv.gz` has columns `listing_id,date,available,minimum_nights,maximum_nights`
  — **no price column**, so month-by-month ADR is not derivable from it; only
  availability/booked-share is. Demand (booked-share) is the honest signal.

## The approach
`scripts/load_demand_curves.py` downloads each latest-snapshot calendar to a
scratch dir (NOT the repo), streams it, and aggregates booked-share
(`available == 'f'`) per calendar month (combining across the ~14 forward months
the snapshot spans) into a compact 12-value curve per listing. It stores that as
JSON on a new `listings.demand_curve` column and **discards the raw calendar** —
storing 35M raw rows would bloat the already-large committed DB. Running it added
~15MB to the DB (190→205MB) and populated all 96,459 listings.

`/api/listings` returns `demand_curve` additively; `static/map.js` parses it,
`metricDemand` returns month-aware booked-share (annual avg when no month
selected), and a JAN–DEC timeline scrubber recolors the Demand layer by month.

**Why:** the task required a *real* seasonal signal, not the old lifetime
review-count proxy. Availability-as-demand is the standard proxy and is far more
real than review counts; the UI labels it honestly ("% booked", "not host-blocked
vs booked" caveat) because `available='f'` conflates booked with host-blocked.

## How to apply / gotchas
- To refresh or add a market: re-run `scripts/load_demand_curves.py` (idempotent;
  it re-derives from the DB's current latest snapshots). It is NOT yet wired into
  the standard load pipeline, so new snapshots won't get curves automatically.
- Booked-share `0.0` is a real value (fully available); `1.0` often means an
  inactive/blocked listing, not hot demand — inherent to availability data.
- Months with no calendar data are stored as `null` in the curve, not fabricated 0.
