---
name: Rentalizer homepage entry-flow pattern
description: How the AIRWORTHY homepage sequences an address into a live estimate, and which shared modules it depends on.
---

The homepage (`templates/index.html` + `static/app.js`) treats the address input as the whole product: no marketing chrome, single input, then a real-response-driven 3-step sequence (locate → comps → resolve) before revealing the result via the shared `AirworthyEnvelope.render()` component (`static/earnings-envelope.js/css`) and `AirworthySaved` (`static/saved-properties.js`) for the save action.

**Why:** the product brief requires the first screen to behave like the product, not a landing page, and other pages (map, report, comparison) reuse the same shared envelope/saved-properties modules — don't reimplement result rendering per page.

**How to apply:** when building the property report or comparison pages, reuse `AirworthyEnvelope.render()` and `AirworthySaved` rather than duplicating revenue-range or save logic. The homepage links to `/property` and `/compare` (not yet implemented as of this task) with query params `address, bedrooms, bathrooms, accommodates, nightly_rate` — match this param naming when building those routes so the homepage links resolve correctly.
