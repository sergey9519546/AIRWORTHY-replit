---
name: Rentalizer desktop SaaS redesign
description: Lessons from converting AIRWORTHY's mobile-app-styled pages into a desktop SaaS layout (persistent nav, map sidebar/inspector, property dashboard).
---

**`element.focus()` on a tall container can scroll a preceding in-flow nav
out of view.** `property.js` calls `reportSection.focus()` after rendering a
report; because the report is much taller than the viewport, the browser's
default scroll-into-view behavior could scroll the page down enough to push
a normal (non-fixed) top nav bar above the fold — even though the nav itself
was `position: sticky`, sticky only re-pins on *user* scroll, and the
programmatic scroll landed the article at the very top on first paint before
any scroll event re-triggered stickiness in some cases. Fix: always pass
`{ preventScroll: true }` to `.focus()` calls on large sections/panels used
purely for a11y-focus-after-async-render, not for visual scrolling.

**Repositioning a Leaflet inspector panel from an absolute overlay to a flex
sibling of the map canvas requires an explicit `map.invalidateSize()`.**
Leaflet caches its container's pixel size; if the container's width changes
because a sibling panel opens/closes (layout-affecting), call
`map.invalidateSize()` (wrapped in `requestAnimationFrame` is enough, no
extra setTimeout needed) right after toggling visibility, or the map renders
stale/cropped until the user manually interacts with it.

**A genuine (non-fabricated) confidence/score gauge can be derived from
`confidence.cv`** (coefficient of variation across comparable revenue
outcomes) using the same thresholds the backend already uses to classify
high/medium/low (cv<0.25 high, cv<0.5 medium, else low): `score = clamp(round((1-cv)*100), 2, 99)`.
This keeps a visual gauge and the textual confidence label always in
agreement, without inventing a separate scoring model.

**Why:** these were each found by direct visual verification (screenshots)
catching a real regression or an opportunity that code review alone would
have missed — the fixes are cheap but easy to skip if you don't screenshot
every restructured page after layout changes.

**How to apply:** whenever moving a nav/panel from a floating/overlay
position to an in-flow or flex-sibling position in this app, re-screenshot
every page that can auto-scroll or resize that region before calling the
work done. This convention applies app-wide, not just the page it was first
found on — audit every `.focus()` call on a section/panel across the app
(homepage, property, map, compare, etc.), not only the one just touched.
