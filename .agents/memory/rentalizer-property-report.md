---
name: Rentalizer property report pattern
description: How the /property earnings report page re-estimates live from comp exclusions and facts edits
---

## Rule
The property report (`templates/property.html`, `static/property.js`) is a single client-rendered
page: it reads `address, bedrooms, bathrooms, accommodates, nightly_rate` from the URL query string,
calls `/v1/estimate`, and re-renders the whole report from the response — there is no server-side
report template logic. Comparable include/exclude and the facts/assumptions editor both work by
re-POSTing to the *same* `/v1/estimate` endpoint with an updated `exclude_comp_ids` list and/or
updated facts (bedrooms/bathrooms/accommodates/nightly_rate/property_type/minimum_nights/
is_superhost/host_listings_count/amenities) — no separate endpoints were added.

Amenity toggles (pool, hot_tub, parking, ev_charger, gym, pet_friendly, workspace) are a genuinely
new request field (`EstimateRequest.amenities`) applied as a small disclosed multiplier in
`enrichment.amenity_multiplier`/`amenity_drivers`, used by both the NYC ML path (`api.py`) and the
comp-based market path (`market_estimator.estimate_from_db`) — kept deliberately minimal/symmetric
across both estimator paths rather than adding amenity modeling to only one.

**Why:** the product brief requires editing property facts to visibly change the live estimate
(not just cosmetic UI state), and the existing `exclude_comp_ids` field already supported this
pattern for comps — extending the same request/response round-trip for facts and amenities avoided
inventing a second contract.

**How to apply:** when extending the report (e.g. a future scenario-lab or verdict feature), prefer
adding fields to `EstimateRequest`/enriching `EstimateResponse` and reusing this same
edit-facts-and-re-POST loop over building a parallel client-only computation, so NYC and non-NYC
markets stay consistent.
