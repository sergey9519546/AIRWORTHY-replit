---
name: AIRWORTHY design direction
description: Where the authoritative AIRWORTHY design/positioning spec lives and the key non-negotiables
---

## Rule
The authoritative AIRWORTHY design + positioning spec is
`airdna-project/08-rentalizer/AIRWORTHY-DESIGN-BRIEF.md` (pointer also in `replit.md`).
All UI work — homepage/cover, map, property report, comparison — must build to it.

Non-negotiables to remember:
- **Positioning:** property-readiness / investment-certification system, NOT an
  "Airbnb calculator." Every property gets a verdict (CLEARED / CONDITIONAL /
  EXPOSED / GROUNDED) + AIRWORTHY score 0–100.
- **Palette:** mineral white `#F2F0E9` canvas, carbon ink `#111310`, **scarce**
  chartreuse `#C9FF45` (selected/positive only), runway orange `#FF623F` (warning),
  atmospheric blue `#4968FF`. No navy, no gold, no purple gradients.
- **Style:** architectural-editorial × precision-instrumentation; thin rules over
  cards; grotesk + mono + one restrained display face; sentence case.
- **Signature motif:** the **Earnings Envelope** (horizontal downside/expected/upside
  forecast field) reused everywhere. Plus subtle "Flight Path" metaphor (NO airplane/
  cockpit icons).
- **Map IS the interface** (~80–100% viewport, one active layer, quiet parcel shading,
  no scattered price bubbles, bottom inspection dock).

**Why:** User uploaded a detailed 2-part creative critique + references synthesis
correcting an earlier "black/gold luxury dashboard" direction, and asked to "decide
best for me." The brief captures it so task agents (#6 map, #7 report, #8 compare)
and homepage rework all inherit one spec and don't drift.

**How to apply:** Read the brief before building/redesigning any AIRWORTHY surface.

## SUPERSEDED 2026-07-13 — the reference image now wins, and it is a LIGHT design
The old "brief text wins over the image" rule was reversed after the user rated a
delivered redesign 1/10. The reference mockup
(`attached_assets/0_Generated_image_1_1783931971613.png`, workspace ROOT dir, not
inside 08-rentalizer; == `image_1783858005252.png`) **IS the spec** — reproduce it.
Key facts that were gotten wrong and must not be repeated:
- **It is LIGHT, not dark.** Do NOT invert the app to a dark hero or dark map — that
  exact move got rejected. Hero = light split: bold black headline + a chartreuse
  accent second line on a near-white/cream bg on the LEFT; a large property photo with
  a floating example-inspection card on the RIGHT. Map = LIGHT tiles (Voyager) with
  charcoal price-pill badges (dark pill + white value + small colored metric dot) —
  the reference DOES have price badges, so the old "no scattered price bubbles" rule is
  superseded (badge only at bounded zoom, ≤~60 listings).
- Chartreuse accent text on white must be deepened (~#5E7A00) for contrast; pure lime
  `#C9FF45` is illegible on white — keep pure lime only on dark chips/verdict fills.
- Two honesty departures from the image remain: no fake partner-trust logos (use honest
  data-source attribution) and no invented "94% accuracy" stat (real backtest figure or
  omit). See the brief's "Honesty adaptations" section.
- **The reference is a full LANDING PAGE, and its two dominant sections are large
  product-showcase panels** — (1) the map-explorer UI (top nav tabs Explore/Market
  pulse/Saved/Reports, left "VIEW LAYER" list w/ icon+text rows, price-range slider,
  type/bedroom selects, price-pill badges on a light map, bottom property strip w/
  Inspect CTA) and (2) the property-report UI (photo+specs, AIRWORTHY score card,
  revenue-range card w/ downside/expected/upside bar, right summary stats, tab row,
  performance-drivers pos/neg list, monthly-forecast bar chart, market summary). These
  live on the homepage as static showcase panels (static/showcase.css + sections in
  templates/index.html), separate from the live /map and /property routes. User wants
  the DESIGN reproduced, not the marketing copy — honest/illustrative copy is fine.
  Rejections happened when these panels were absent, so the homepage read as "nothing
  like the reference beyond the background color."
