---
name: Rentalizer real photos & sources
description: Durable lessons for real listing/property photo enrichment (InsideAirbnb + Firecrawl) in the rentalizer estimate flow.
---

## Photo data already exists in the raw sources
InsideAirbnb's raw CSVs (both the NYC training set and the general comp
database) carry real `picture_url`/`listing_url` columns — this is existing
data that just wasn't being read, not something to synthesize. When a
"show real X" ask sounds like it needs new data, check the raw source first.

## Enrichment calls in the estimate critical path must be timeout-bounded
against the FRONTEND's abort timeout, not just individually "fail-open"
tuned in isolation. `/v1/estimate` already makes one enrichment call
(Realie); a second one (Firecrawl) was added inline. Each call being
individually fail-open (catches its own exceptions, returns None) is
necessary but not sufficient — if a *slow-but-not-erroring* provider's
timeout is close to or exceeds the client's fetch-abort timeout, the whole
estimate can appear to "fail" from the user's perspective even though the
backend eventually would have returned fine.

**Why:** a code reviewer caught this after implementation — the initial
Firecrawl timeout (25s) exceeded the frontend's 15s abort, and it was
stacked sequentially after another 6s-timeout enrichment call.

**How to apply:** when adding any inline enrichment call to a request path
that has a client-side timeout, (1) keep the backend timeout well under the
client timeout, and (2) if multiple independent enrichment calls exist on
the same path, run them concurrently (e.g. `asyncio.gather` +
`asyncio.to_thread` for blocking `requests` calls) so their timeouts don't
sum — worst case should be `max()` of the enrichment timeouts, not their sum.

## Real photo sources sometimes return non-photo placeholder images
A real-estate site's og:image can be a generic "no photography available"
stock image or a referrer-locked static-map screenshot rather than an actual
listing photo — still a technically valid, loadable-by-curl image URL. Two
independent failure modes to expect: (1) known placeholder filename patterns
(filter by substring), and (2) images that 403/fail specifically when loaded
from a browser context with a different referrer/domain than expected (curl
succeeds, browser `img.onerror` fires) — the client-side `onerror` fail-open
handler is the real safety net for this second case, not the backend filter.
