# AIRWORTHY — Design Brief (single source of truth)

> This is the authoritative design + product-positioning spec for AIRWORTHY. Every
> surface (homepage/cover, map, property report, comparison) and every task agent
> must build to **this document**. It synthesizes the two written creative-direction
> docs. Where the reference **mockup image disagrees with this text, the text wins**
> (see "Reference image caveat" at the end).
>
> Source references (uploaded):
> - `attached_assets/Pasted--A-Quick-Guide-to-Short-Term-Rental-Financing-*.txt` — creative critique + page specs
> - `attached_assets/Pasted--Lewa-House-Unseen-Studio-*.txt` — references synthesis ("Predictive Property Atlas")
> - `attached_assets/image_1783858005252.png` — approximate mockup (NOT to be reproduced literally)

---

## 1. Positioning

AIRWORTHY is **not** an "Airbnb calculator." It is a **property-readiness /
investment-certification system**:

> **Determine whether a property is AIRWORTHY before you buy, list, or operate it.**

Every property resolves to a **verdict** plus an **AIRWORTHY score (0–100)**:

| Verdict | Meaning |
| --- | --- |
| **CLEARED** | Strong projected performance |
| **CONDITIONAL** | Viable under specific assumptions |
| **EXPOSED** | Financially sensitive |
| **GROUNDED** | Insufficient earnings potential |

Aviation influences the **decision logic**, never the decoration. No airplane icons,
wings, compass logos, cockpit gauges, or runway graphics.

---

## 2. Creative concept

**Architectural editorial × precision instrumentation** — think high-end
architectural publication + professional underwriting report + calm geospatial
intelligence platform. Reduce noise, preserve focus (Linear-style calm), let the
**product's function generate the brand language** (Studio Freight method).

Overarching idea: **Predictive Property Atlas** — a living spatial model of a
property's earning future. The user inspects the forces that produced an estimate,
not just the number.

---

## 3. Visual system

### Palette (avoid navy + gold entirely)

| Role | Color |
| --- | --- |
| Primary canvas | Mineral white `#F2F0E9` |
| Secondary canvas | Bone `#E8E5DC` |
| Primary ink | Carbon `#111310` |
| Secondary text | Graphite `#686A64` |
| Positive signal | Electric chartreuse `#C9FF45` |
| Warning signal | Runway orange `#FF623F` |
| Analytical blue | Atmospheric blue `#4968FF` |
| Dark map | Near-black green `#111713` |

**Chartreuse is scarce** — only selected properties, active controls, and positive
status. Its recognizability comes from restraint.

### Typography (three coordinated voices)

- **Editorial grotesk** — product narrative / headlines
- **Technical mono** — coordinates, assumptions, source data, metric labels
- **Condensed display face** — revenue figures and status
- Large numerals, narrow metric labels, generous whitespace, **sentence case**
  (not uppercase everywhere). Do NOT use a luxury fashion serif for every headline;
  at most one restrained serif for a single major statement.

### Interface geometry

- Fewer cards; **thin structural rules** instead of containers
- Large uninterrupted surfaces; strong 12-column architectural grid
- Slightly squared radii (8–12px)
- No glassmorphism; no shadows unless indicating real physical elevation

### Graphic materials (native to the product, not motifs)

Topographic contours, parcel outlines, cadastral grids, seasonal solar paths,
occupancy traces, comparable-property vectors, forecast frames, confidence
boundaries, geographic coordinates, architectural sections, revenue elevation fields.

---

## 4. Signature brand devices

### The Earnings Envelope (primary motif — reuse everywhere)

A horizontal forecast field, NOT bars/line charts:

```
DOWNSIDE          EXPECTED RANGE               UPSIDE
───────────────████████████████████──────────────────
$61K             $78K          $94K             $108K
```

It updates as assumptions/comps/market change, and is the hero visual, property-page
visualization, comparison visualization, saved-property thumbnail, and report cover.

### Flight Path (subtle aviation metaphor — appears once)

A thin trajectory: `PROPERTY → MARKET CONDITIONS → OPERATING ASSUMPTIONS → REVENUE OUTCOME`.
Changing an assumption bends the trajectory: strong→Cleared, sensitive→Conditional,
unstable→Exposed, nonviable→Grounded.

---

## 5. Surface specs

### A. Cover / homepage
- Feels like an **immediate property inspection**, not a marketing page.
- Headline: "Is this property ready to perform?" / "What could this property earn?"
- Large **address command field** ("Enter an address, listing URL, or parcel ID →")
  over a restrained, continuously moving geographic field — **not a mansion photo**.
- Live inspection preview already shows: verdict (e.g. CONDITIONAL), expected annual
  revenue **range**, confidence + verified-comparable count.
- Progressive product demo, not "hero → logos → feature cards → testimonial → CTA":
  locate parcel → building rises → comparables emerge → evidence network → seasonal
  waves → forecast range resolves → verdict.

### B. Map search (map IS the interface)
- Map ≈ **80–100% of viewport**. No permanent oversized filter column — a narrow
  contextual rail that changes by workflow.
- Top command bar: `Austin, TX   Revenue ▾   3 BR ▾   Entire home ▾` and mode tabs
  (Market / Property / Compare).
- **One primary layer active at a time**: Revenue potential, Occupancy, ADR,
  Seasonality, Supply pressure, Regulation exposure, Investment resilience.
- Map behavior: quiet parcel shading at market level; revenue clusters when zoomed
  out; individual markers only when zoomed in; a single high-contrast selected
  property; automatic decluttering; contextual neighborhood boundaries; restrained
  integrated legend. **Do NOT scatter `$92K/$67K/$31K` bubbles everywhere.**
- Bottom **inspection dock** on selection (address, AIRWORTHY score + verdict,
  revenue range, occupancy, ADR, comparable count, "Inspect property →") — keeps the
  user on the map instead of opening big floating cards.
- Optional **bottom timeline** (JAN…DEC): dragging months transforms the map
  (building elevation ~ expected revenue, demand density, ADR pressure, confidence).

### C. Property intelligence report (decision brief, not a dashboard grid)
Ordered hierarchy:
1. **Decision summary** — one paragraph explaining the verdict.
2. **Earnings envelope** — conservative / expected / strong / downside threshold.
3. **Performance drivers** — signed `+`/`−` list of what helps/hurts.
4. **Comparable evidence / constellation** — subject at center; comps positioned by
   *similarity* (not just distance); each has match score, distance, bed/guest match,
   amenity diff, revenue, ADR, occupancy, include/exclude control, reason.
5. **Scenario laboratory** — adjust occupancy, ADR, cleaning/mgmt/platform fees,
   opex, seasonality, improvements; range + status update immediately.
6. **Decision footer** — AIRWORTHY verdict + [Save analysis] [Compare another] [Export report].
- Central number is a **range** (`$78,400–$94,100`), not false precision; support with
  central estimate, confidence, comparable quality ("31 of 44 accepted"), forecast
  horizon, data recency. Differentiate by showing **why to trust it and where it fails**.
- Optional distinctive extra: **building cutaway** attributing revenue contribution
  (e.g. `POOL +$9.8K`, `FOURTH BEDROOM +$7.1K`, `DISTANCE FROM CORE −$5.2K`).

### D. Comparison
Uses the Earnings Envelope as the comparison visualization across properties.

---

## 6. Remove / never do

Black-and-gold luxury styling · giant mansion hero · generic abstract hexagon logo ·
four identical feature cards · floating map price bubbles everywhere · tiny text in a
three-screen montage · random AI sparkle icons · **fake partner logos**
(airbnb/vrbo/booking/expedia/zillow) · "Trusted by 12,000+ investors" filler · every
statistic inside a rounded rectangle · decorative charts that don't support a
decision · unqualified accuracy claims ("94%/98% accuracy") · aviation clichés ·
generic "premium dark mode" · purple heatmaps/gradients.

---

## 7. Implementation notes

- Include structured-data schema at the end of the app: `Organization`, `WebSite`,
  `SoftwareApplication`, `FAQPage`.
- Map styling should not look like default Google Maps — remove irrelevant POIs,
  control marker visibility, prioritize meaningful layers (Mapbox real-estate guidance).

---

## Reference image caveat

`attached_assets/image_1783858005252.png` is an **approximate** mockup. It still
contains multiple things this brief explicitly forbids: scattered `$78K/$92K/$67K`
map price bubbles, a KPI card per stat, the airbnb/vrbo/booking/expedia/zillow
partner-logo row, the four-step "How AIRWORTHY works" cards, "Trusted by investors,"
and a "94% accuracy" claim. **Follow this text, not the image**, wherever they
conflict. Use the image only for general layout intuition (mineral canvas, chartreuse
accent, editorial headline, map + report composition).
