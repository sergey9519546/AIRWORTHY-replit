# Anti-Bot Bypass

> How to scrape at scale without getting blocked

---

## Airbnb's Anti-Bot Stack
- **Akamai Bot Manager** — primary anti-bot
- **Cloudflare** — secondary protection
- **Rate limiting** — per IP
- **Fingerprinting** — browser fingerprint analysis
- **CAPTCHA** — Arkose Labs, reCAPTCHA

## Tools for Bypass

### Tier 1: Stealth Playwright
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    # Remove automation fingerprints
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
    """)
```

### Tier 2: Undetected ChromeDriver
```python
import undetected_chromedriver as uc

driver = uc.Chrome(headless=True)
driver.get("https://www.airbnb.com")
```

### Tier 3: Scrapling (Python)
```python
from scrapling import Adaptor, StealthyFetcher

fetcher = StealthyFetcher()
page = fetcher.fetch("https://www.airbnb.com/rooms/12345")
```

### Tier 4: Scrapfly (SaaS API)
```python
from scrapfly import ScrapflyClient, ScrapeConfig

client = ScrapflyClient(key="YOUR_KEY")
result = client.scrape(ScrapeConfig(
    url="https://www.airbnb.com/rooms/12345",
    render_js=True,
    anti_bot=True,
    country="US",
))
```

## Proxy Strategy

### Residential Proxies (for Airbnb)
| Provider | Pool Size | Cost |
|---|---|---|
| Bright Data | 72M+ IPs | $500+/mo |
| Oxylabs | 100M+ IPs | $300+/mo |
| Smartproxy | 40M+ IPs | $200+/mo |
| Decodo | 55M+ IPs | $150+/mo |

### Rotation Strategy
- 1 request per 2-3 seconds per IP
- Rotate proxy per request
- Session-based proxies for authenticated endpoints
- Residential for Airbnb, datacenter for Vrbo/Booking

## Rate Limiting
```python
import time
import random

def safe_request(url, headers, body):
    """Request with rate limiting and retry."""
    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=body)
            if resp.status_code == 429:
                wait = int(resp.headers.get('Retry-After', 60))
                time.sleep(wait)
                continue
            return resp
        except Exception as e:
            time.sleep(5 * (attempt + 1))
    
    return None
```

## What Triggers Blocks
- Too many requests per IP
- Missing/invalid User-Agent
- Missing cookies
- Headless browser detection
- Consistent request patterns
- Geographic mismatch (proxy vs account)

## Best Practices
- Rotate proxies per request
- Randomize request timing (2-5 seconds)
- Use real browser fingerprints
- Maintain session cookies
- Respect Retry-After headers
- Monitor for 403/429 responses
