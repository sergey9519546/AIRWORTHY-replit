# Airbnb Search / Listing Discovery

> How to discover listings at scale via search

---

## The StaysSearch GraphQL Operation

Airbnb's search results are powered by `StaysSearch` GraphQL operation. Key discovery from browse.sh:

### How It Works
- The `/api/v3/StaysSearch` endpoint uses **rotating persisted-query hashes** + device fingerprinting
- Direct API calls fail without proper browser context
- **BUT:** The StaysSearch response is rendered inline as a **~380 KB JSON blob** in `<script id="data-deferred-state-0">` on every `/s/{slug}/homes` page
- Parsing that blob is dramatically more reliable than DOM-scraping

### Search URL Pattern
```
https://www.airbnb.com/s/{URL-encoded-slug}/homes?{filters}
```

**Always use `/homes` at the end.** Plain `/s/{slug}` sometimes 301-redirects to `/{city}/stays` which returns a 503 error.

### Filter Parameters (URL-encodable)

| Parameter | Description |
|---|---|
| `checkin=YYYY-MM-DD` | Check-in date |
| `checkout=YYYY-MM-DD` | Check-out date |
| `adults=N` | Number of adults |
| `children=N` | Number of children (age 2-12) |
| `infants=N` | Number of infants (under 2) |
| `pets=N` | Number of pets |
| `min_bedrooms=N` | Minimum bedrooms |
| `min_beds=N` | Minimum beds |
| `min_bathrooms=N` | Minimum bathrooms |
| `price_min=N` | Minimum price (in storefront currency) |
| `price_max=N` | Maximum price |
| `display_currency=USD` | Currency code |
| `room_types[]=Entire%20home%2Fapt` | Place type |
| `property_type_id[]=N` | Property type (House, Apartment, etc.) |
| `amenities[]=N` | Amenity IDs (4=Wi-Fi, 8=Kitchen, etc.) |
| `ib=true` | Instant Book |
| `fc=true` | Free cancellation |
| `superhost=true` | Superhost only |
| `ne_lat`, `ne_lng`, `sw_lat`, `sw_lng` | Map bounding box |
| `search_by_map=true` | Required with bbox |
| `items_offset=N` | Pagination (steps of 18) |
| `category_tag=Tag:NNNN` | Category rail filter |

### Pagination
- `items_offset=0` → first 18 results
- `items_offset=18` → next 18
- `items_offset=36` → next 18
- Continue until no more results

### Listing ID Discovery
From search results, extract listing IDs to then call:
```
GET https://www.airbnb.com/rooms/{listing_id}?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD&adults=N
```

The PDP page also contains `<script id="data-deferred-state-0">` with `StaysPdpSections` data.

### Amenity ID Enum (Undocumented but Stable)
| ID | Amenity |
|---|---|
| 4 | Wi-Fi |
| 8 | Kitchen |
| ... | (discover from Filters modal URL) |

### Category Tags (Undocumented)
| Tag | Category |
|---|---|
| Tag:8536 | Amazing views |
| ... | (discover from /categories page) |

---

## Implementation Strategy

### Option 1: Browser Automation (Recommended)
```python
from playwright.sync_api import sync_playwright

def search_airbnb(location, checkin, checkout, adults=2):
    url = f"https://www.airbnb.com/s/{location}/homes?checkin={checkin}&checkout={checkout}&adults={adults}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        
        # Extract the SSR JSON blob
        blob = page.evaluate("""
            () => {
                const el = document.getElementById('data-deferred-state-0');
                return el ? JSON.parse(el.textContent) : null;
            }
        """)
        
        # Parse listings from blob
        listings = extract_listings(blob)
        return listings
```

### Option 2: Direct SSR Fetch (No Browser)
```python
import requests
from bs4 import BeautifulSoup
import json

def search_airbnb_direct(location, checkin, checkout):
    url = f"https://www.airbnb.com/s/{location}/homes?checkin={checkin}&checkout={checkout}"
    headers = {'User-Agent': 'Mozilla/5.0 ...'}
    
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    blob_el = soup.find('script', id='data-deferred-state-0')
    if blob_el:
        blob = json.loads(blob_el.string)
        return extract_listings(blob)
    return []
```

**Note:** Direct fetch may be blocked by PerimeterX. Browser automation with stealth is more reliable.

---

## What You Get Per Listing

From the StaysSearch blob:
- Listing ID
- Title
- Listing type (Entire home, Private room, etc.)
- Host info
- Location + coordinates
- Bedroom/bed/bath counts
- Max guests
- Amenity highlights
- Photo URLs
- Nightly + total pricing
- Cleaning/service fees
- Rating
- Review count
- Superhost / Instant Book / Free cancellation badges
- Canonical `/rooms/{id}` URL
