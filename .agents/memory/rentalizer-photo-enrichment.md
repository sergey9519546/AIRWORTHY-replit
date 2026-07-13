---
name: Rentalizer real photos & sources
description: Where listing/property photos come from, and how the hero photo gallery is mined without extra scrape calls.
---

- Comp photos: `picture_url` only, sourced from InsideAirbnb CSV/DB (`data/train.csv` + comp DB). No gallery field exists upstream (`xl_picture_url`/similar are not present) — a comp gallery needs a per-comp scrape of each comp's own Airbnb `listing_url`, which is unbounded/slow across dozens of comps, so it's intentionally out of scope for the hero-photo gallery.
- Searched-property hero gallery: mined for free from the same Firecrawl `/v1/search` call already used for the single photo — request `scrapeOptions.formats: ["markdown"]`, then regex-scan the winning result's `markdown` field for `![alt](url)` images on the *same host* as the primary photo. No second network call needed; Firecrawl renders JS so client-side-loaded carousel images still show up in markdown.
- Some sites (Zillow) serve a bot/no-JS shell with a generic `share_thumbnail.png` og:image instead of the real listing when scraped — treat as a placeholder (added to `_PLACEHOLDER_MARKERS`) so `_pick_photo` falls through to the next site instead of keeping site-wide junk.
- Some CDNs (e.g. PropertyShark) send `Cross-Origin-Resource-Policy` headers that block direct `<img>` hotlinking in the browser (`ERR_BLOCKED_BY_RESPONSE.NotSameOrigin`) even though the URL is fetchable server-side. Not fixable via `crossorigin`/`referrerpolicy`; only a server-side image proxy fixes it. Existing `onerror` fail-open handling is the mitigation until that's built.
