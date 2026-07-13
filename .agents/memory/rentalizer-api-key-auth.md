---
name: Rentalizer /v1/estimate auth model
description: Decision on how AIRWORTHY's estimate endpoints authenticate browser vs. partner callers without any spoofable exemption.
---

Every call to `/v1/estimate` and `/v1/batch` must present a valid `X-API-Key` header — there is no same-origin, cookie, or header-based exemption. Two tries at building a browser exemption (trusting Origin/Referer/Sec-Fetch-Site headers, then a signed session cookie issued on page load) were both rejected in review: both let a plain script obtain "browser" access without ever needing a real key, which defeats "require an API key."

The browser pages instead get a real, valid key like anyone else: a single public, low-privilege `BROWSER_API_KEY` is rendered server-side into each page (meta tag) and attached as `X-API-Key` by client JS — the same trust model as a Stripe publishable key or Google Maps browser key. It is intentionally visible in page source; it is not a bypass of the header requirement, just the specific key the web UI uses.

**Why:** any exemption keyed off client-supplied signals (headers, or a cookie obtainable by simply loading a public page) is equivalent to no auth at all for that path — reviewers should reject it. Requiring every caller, including the browser, to present *some* valid key keeps "presence of a valid key" as the actual gate.

**How to apply:** if a new client-side call needs API access, give it the existing browser key (already wired via `static/api-key.js` + the `airworthy-browser-key` meta tag) rather than inventing another exemption. Missing `API_KEYS` config still fails closed in production and open only in local dev (`REPLIT_DEPLOYMENT` unset).
