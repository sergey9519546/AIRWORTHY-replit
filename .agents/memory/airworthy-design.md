---
name: AIRWORTHY design direction
description: Current design system for the Rentalizer/AIRWORTHY app — clean light SaaS, single source of truth is tokens.css; the old design brief is retired.
---

# AIRWORTHY design direction

**Current system (2026-07-13):** Clean, light, modern SaaS. White/near-white
surfaces, near-black text, cool-gray hairline borders, ONE refined chartreuse
accent, near-black pill CTAs, and a single sans-serif (Inter) for everything.
Visual target = the user's reference mockup (`attached_assets/Generated_image_1_*.png`).

**Single source of truth = `airdna-project/08-rentalizer/static/tokens.css`.**
Every page loads it first, then a page-specific sheet. Change values there to
re-skin the whole app at once. Key moves that make it high-leverage:
- All font-role tokens (`--aw-font-ui/display/display-condensed/mono`) resolve to
  Inter. Mapping `--aw-font-mono` -> Inter neutralizes the old monospace
  "instrumentation" labels app-wide without editing every file. Small UPPERCASE
  letter-spaced micro-labels are fine and on-target (the reference uses them too)
  — they just render in Inter now, not mono.
- Legacy token NAMES were kept (colors + `--coral*`, `--font`, `--color-*`
  aliases) so existing page CSS keeps resolving; only values changed.
- Accent lime `#B4E24D`; readable lime text on light = `--aw-lime-ink` `#47600A`
  (pure lime is illegible on white). Blue `#6472FF` = analytical/forecast; coral
  `#F04438` = downside. Verdicts map onto these.

**Retired (do NOT reinstate):** `AIRWORTHY-DESIGN-BRIEF.md` was DELETED at the
user's explicit request, and the pointer in `replit.md` was rewritten. The old
"mineral-white canvas / Space Grotesk / editorial×instrument / cream `#F2F0E9`"
direction is no longer a source of truth.
**Why:** the user rejected that look 4+ times as not matching their reference and
asked to "get rid of the design system I can't get rid of." The reference image
is the spec now.

**Map page pattern:** the left rail is a text "View layer" sidebar (not an icon
rail): text-label buttons with a small square icon, muted by default, lime-tint
(`--aw-lime-tint` bg + ink text) when active. Buttons keep their `data-layer`
values (revenue/adr/occupancy/demand/density) so `map.js` is untouched.

**Dev gotcha:** static CSS is browser-cached; after editing a `.css` the app
preview can screenshot stale styling. Confirm the served file with
`curl .../static/<file>.css | grep <new-rule>`; the source is correct even when
the screenshot looks old — re-screenshot to force revalidation.
