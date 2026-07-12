---
name: Rentalizer property comparison page
description: How /compare works — single flex-row layout, per-card independent estimate fetches, shared facts shape across pages.
---

- `/compare` (templates/compare.html + static/compare.js/css) renders each compared property as its own card with an independent `/v1/estimate` fetch/state (loading/ready/error), so adding, removing, or retrying one card never touches the others.
- One property "facts" shape (`{address, bedrooms, bathrooms, accommodates, nightly_rate}`) is shared end-to-end: homepage → property report → `/compare?...` query params → the compare page's "add by address" form. Keep new entry points to comparison consistent with this shape.
- The comparison grid is a single `display:flex; overflow-x:auto; scroll-snap-type:x` row (compare.css `.compare-grid`) — this alone gives side-by-side on wide viewports and swipeable/stacked on narrow ones, no separate mobile layout needed.
- AirworthySaved (static/saved-properties.js) does not store bathrooms, so "add from saved" on the compare page defaults bathrooms to 1 — a known gap (see follow-up task on this topic).
