# Session Cookie Extraction

> How to get authenticated cookies for calendar/availability endpoints

---

## The Problem
Airbnb's `PdpAvailabilityCalendar` GraphQL endpoint returns 403 without session cookies. The calendar data is essential for booking detection.

## Solution 1: Playwright with Cookie Extraction

```python
from playwright.sync_api import sync_playwright
import json

def extract_airbnb_cookies():
    """Visit Airbnb and extract session cookies."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        
        page = ctx.new_page()
        
        # Visit Airbnb to get cookies
        page.goto("https://www.airbnb.com/", wait_until="networkidle", timeout=30000)
        
        # Extract cookies
        cookies = ctx.cookies()
        
        browser.close()
    
    # Filter for relevant cookies
    relevant = {c['name']: c['value'] for c in cookies 
                if any(x in c['name'].lower() for x in ['bev', 'everest', 'user_attributes', 'country', 'session'])}
    
    return relevant

# Use cookies with requests
import requests

cookies = extract_airbnb_cookies()
headers = {
    'Content-Type': 'application/json',
    'X-Airbnb-Api-Key': 'd306zoyjsyarp7ifhu67rjxn52tv0t20',
    'User-Agent': 'Mozilla/5.0 ...',
}

# Now call calendar endpoint with cookies
resp = requests.post(
    'https://www.airbnb.com/api/v3/PdpAvailabilityCalendar/...',
    headers=headers,
    cookies=cookies,
    json=calendar_payload
)
```

## Solution 2: Use the SSR Blob (No Auth Needed)

The search results page embeds calendar data in the SSR blob. For individual listings:

```python
def get_listing_calendar(listing_id, checkin, checkout):
    """Get calendar data from the listing page SSR blob."""
    url = f"https://www.airbnb.com/rooms/{listing_id}?check_in={checkin}&check_out={checkout}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        
        # Extract SSR blob
        blob = page.evaluate("""
            () => {
                const el = document.getElementById('data-deferred-state-0');
                return el ? JSON.parse(el.textContent) : null;
            }
        """)
        
        browser.close()
    
    # Parse calendar from StaysPdpSections
    if blob:
        sections = blob.get('niobeClientData', [{}])[0][1]
        # ... parse calendar data from sections
        return sections
    return None
```

## Solution 3: HAR Capture (Manual but Reliable)

1. Open Chrome DevTools → Network tab
2. Browse Airbnb listing pages
3. Look for `PdpAvailabilityCalendar` requests
4. Right-click → Copy as cURL
5. Extract cookies from the cURL command

## Key Cookies

| Cookie | Purpose |
|---|---|
| `bev` | Session identifier |
| `everest_cookie` | Device fingerprint |
| `_user_attributes` | User preferences (currency, etc.) |
| `country` | Country code |
| `OptanonConsent` | Cookie consent |

## Rate Limiting
- Cookies expire after ~30 days
- Refresh cookies daily for production use
- Use proxy rotation with cookie rotation
