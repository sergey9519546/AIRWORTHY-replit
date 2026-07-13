---
name: Rentalizer per-key rate limits
description: How /v1/estimate & /v1/batch rate-limit per API key, and the slowapi dynamic-limit gotcha
---

# Per-key rate limiting (src/api.py)

Rate limits key off the authenticated **partner** API key when present, else fall
back to per-IP. Config: `RATE_LIMIT_ESTIMATE`/`RATE_LIMIT_BATCH` (defaults
30/min, 5/min) plus optional per-key overrides `API_KEY_RATE_LIMITS` /
`API_KEY_BATCH_RATE_LIMITS` as `"<key>=<limit>,<key>=<limit>"`.

**Why the shared browser key is NOT keyed:** every caller (incl. the browser)
sends an X-API-Key, but the public `BROWSER_API_KEY` is shared by all visitors.
`verify_api_key` records `request.state.api_key` only for real API_KEYS members;
browser/dev traffic is left None so it buckets per-IP — otherwise all browser
users collapse into one bucket.

**slowapi dynamic-limit gotcha:** a callable passed to `@limiter.limit(...)`
only receives the resolved rate-limit key if its parameter is literally named
`key` (slowapi inspects the signature for that exact name). Any other name →
it's called with no args and raises. The custom `key_func` tags partner traffic
`"key:<api_key>"` and everything else `"ip:<addr>"`; the limit provider strips
the `key:` prefix to look up the budget.

**How to apply:** don't rename the `key` param on `_estimate_limit`/`_batch_limit`.
When keys become dynamic (issue/revoke without redeploy), the per-key
budget lookup should move off env vars to the same dynamic store.

**Rate-limit headers (X-RateLimit-* / Retry-After):** require
`Limiter(..., headers_enabled=True)`. slowapi injects headers on a *success*
response only if the endpoint returns a starlette `Response` OR declares a
`response: Response` param — our endpoints return pydantic models/lists, so both
`/v1/estimate` and `/v1/batch` must keep the `response: Response` param or the
headers silently vanish on 2xx (they'd still appear on 429).

**Custom 429 body:** `RateLimitExceeded` is a starlette HTTPException; without an
explicit handler FastAPI's default renders an opaque `{"detail":"30 per 1 minute"}`.
Register `@app.exception_handler(RateLimitExceeded)` and call
`limiter._inject_headers(response, request.state.view_rate_limit)` to keep the
headers on the 429. Retry seconds = `1 + get_window_stats(...)[0] - time.time()`.
**Why:** partners need to self-throttle and know when to retry, not guess.
