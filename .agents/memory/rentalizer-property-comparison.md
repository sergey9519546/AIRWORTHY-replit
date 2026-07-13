---
name: Rentalizer property comparison page
description: How /compare gets seasonal demand-curve data and highlights differences across cards
---

## Demand curve for compared properties
`/v1/estimate` now also returns `demand_curve` (12-value Jan..Dec booked-share array, or null).
It is NOT reused from whatever comp set produced the revenue number — NYC's ML-model comps come
from `train.csv` with a different id space than `db/airbnb.db`'s `listings.id`, so comp ids can't
be trusted to look up `demand_curve` there. Instead a dedicated lookup
(`market_estimator.get_demand_curve`) re-queries the listings DB directly by lat/lng + bedroom
similarity, independent of the revenue estimation path. This means NYC addresses correctly get
`null` (no listings-DB coverage there), while CA/FL addresses get a real curve — a "graceful empty
state" is expected behavior, not a bug.

**Why:** avoids silently attaching the wrong property's seasonality just because an id happened
to collide, and keeps the demand-curve feature decoupled from which estimation branch ran.

**How to apply:** if a new market path is added (a new ML model, a new comp index), don't assume
its comp ids map into `db/airbnb.db`. Reuse `get_demand_curve(conn, lat, lng, bedrooms, room_type)`
instead of piggybacking on that path's own comps.

## Cross-card difference highlighting
`/compare` tags DOM elements with `data-metric`/`data-metric-value` (revenue, score, adr,
occupancy, comps) and, once 2+ cards are ready, marks the single highest (▲) and lowest (▼) value
per metric — never a fabricated overall "winner". See `updateHighlights()` in `compare.js`.
