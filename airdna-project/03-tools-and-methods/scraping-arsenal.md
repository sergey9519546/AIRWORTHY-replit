# Scraping Arsenal

> Tools and techniques for data collection

---

## Tier 1: Shadow API (Best Approach)
Call Airbnb's internal GraphQL endpoints directly.

**Tool:** curl / Python requests
**Pros:** Fast, clean JSON, no HTML parsing
**Cons:** Some endpoints need session cookies

```bash
curl -X POST 'https://www.airbnb.com/api/v3/StaysPdpSections/{hash}' \
  -H 'X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20' \
  -H 'Content-Type: application/json' \
  -d '{"operationName":"StaysPdpSections",...}'
```

## Tier 2: HAR File Capture
Capture what your browser sees.

**Tool:** Chrome DevTools + Stevesie
**Pros:** Legal, simple, no coding
**Cons:** Manual, limited scale

1. Open DevTools → Network tab
2. Browse AirDNA/Airbnb
3. Export HAR file
4. Parse with Stevesie or custom script

## Tier 3: Playwright + CDP
Automated browser with full traffic interception.

**Tool:** Playwright (Python)
**Pros:** Handles SPAs, captures all requests
**Cons:** Slower, resource-intensive

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", handle_response)
    page.goto("https://www.airbnb.com/rooms/12345")
```

## Tier 4: Unbrowse
Auto-discovers shadow APIs.

**Tool:** `npx unbrowse setup`
**Pros:** Automatic endpoint discovery
**Cons:** Large package, slow install

```bash
unbrowse go https://www.airbnb.com
# Browse the site
unbrowse snap
unbrowse skill airbnb.com
```

## Anti-Bot Bypass

| Tool | Type | Capability |
|---|---|---|
| Scrapfly | SaaS | Auto-rotating proxies, anti-bot |
| Scrapling | Python lib | Adaptive scraping |
| Crawlee | Node.js | Playwright + proxy rotation |
| Playwright Stealth | Plugin | Removes automation fingerprints |
| Undetected ChromeDriver | Python | Patches ChromeDriver |

## Proxy Providers

| Provider | Residential | Datacenter | Cost |
|---|---|---|---|
| Bright Data | ✓ | ✓ | $500+/mo |
| Oxylabs | ✓ | ✓ | $300+/mo |
| Smartproxy | ✓ | ✓ | $200+/mo |
| Decodo | ✓ | ✓ | $150+/mo |

## Rate Limiting
- Airbnb: ~1 request per 2-3 seconds per IP
- Use rotating proxies for scale
- Respect `Retry-After` headers
- Back off on 429 errors
