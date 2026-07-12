---
name: Rentalizer market map layers
description: How the /map page derives its analytical layers and inspection-panel revenue range without changing the /api/listings contract.
---

The market map (`static/map.js`) intentionally avoids adding new query params or
columns to `/api/listings`. ADR = `price_numeric` directly; occupancy =
`estimated_revenue_l365d / (price_numeric * 365)`; demand is a review-count
proxy (no real monthly data exists per listing); comparable density is a
client-computed haversine radius count. Bedrooms/guests/revenue-range filters
are applied client-side against the already-fetched bounding-box result, not
sent as new API params.

The inspection panel's Earnings Envelope range is computed from nearby comps
(same room_type within ~1.5mi) using p10/p50/p90 of their `estimated_revenue_l365d`,
not a fabricated percentage band — falls back to a narrow ±20% band around the
listing's own modeled revenue only when fewer than 4 comps exist, with
confidence downgraded to "low" in that case.

**Why:** the map task's brief explicitly scoped out changing the listings API
contract/data coverage, so every new layer/filter had to be derived from
existing response fields rather than requiring backend changes.

**How to apply:** if the property-report or comparison tasks need the same
derived ADR/occupancy/comp-range logic, check `static/map.js` for the exact
formulas before reimplementing — keep them consistent across pages.
