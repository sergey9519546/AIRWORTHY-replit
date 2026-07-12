# Working Examples — Airbnb Shadow API

> Tested, confirmed working API calls

---

## Example 1: Get Listing Detail (Pricing, Rules, Availability)

```bash
curl -s -X POST \
  'https://www.airbnb.com/api/v3/StaysPdpSections/3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d' \
  -H 'Content-Type: application/json' \
  -H 'X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -H 'Accept: application/json' \
  -H 'Origin: https://www.airbnb.com' \
  -d '{
    "operationName": "StaysPdpSections",
    "variables": {
      "id": "U3RheUxpc3Rpbmc6MTI5OTIyMjc5Mjc3OTAwNTE3MQ==",
      "pdpSectionsRequest": {
        "adults": "1", "children": "0", "infants": "0", "pets": 0,
        "checkIn": "2026-07-15", "checkOut": "2026-07-20",
        "layouts": ["SIDEBAR", "SINGLE_COLUMN"],
        "privateBooking": false
      },
      "dateRange": {"startDate": "2026-07-15", "endDate": "2026-07-20"},
      "guestCounts": {"numberOfAdults": 1, "numberOfChildren": 0, "numberOfInfants": 0, "numberOfPets": 0},
      "includeGpBookItFragment": true,
      "includeGpAmenitiesFragment": true,
      "includeGpReviewsFragment": true,
      "includeGpPoliciesFragment": true
    },
    "extensions": {
      "persistedQuery": {"version": 1, "sha256Hash": "3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d"}
    }
  }' | python3 -m json.tool
```

**Status:** ✅ Working (200 OK, 60KB response)

**Extracted Data:**
```json
{
  "discountedPrice": "$1,715 SGD",
  "originalPrice": "$1,931 SGD",
  "qualifier": "for 5 nights",
  "available": true,
  "maxGuestCapacity": 4,
  "priceBreakdown": [
    {"description": "5 nights x $319.27 SGD", "price": "$1,596.33 SGD"},
    {"description": "Long stay discount", "price": "-$216.09 SGD"},
    {"description": "Resort fee", "price": "$334.55 SGD"}
  ],
  "houseRules": [
    {"title": "Check-in", "subtitle": "4:00 PM - 12:00 AM"},
    {"title": "Checkout before", "subtitle": "11:00 AM"},
    {"title": "4 guests maximum", "subtitle": ""}
  ],
  "cancellation": "Free cancellation before July 3"
}
```

## Example 2: Python Script

```python
import requests
import base64

API_KEY = "***"
BASE = "https://www.airbnb.com/api/v3"

headers = {
    'Content-Type': 'application/json',
    'X-Airbnb-Api-Key': API_KEY,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Origin': 'https://www.airbnb.com',
}

def get_listing_detail(listing_id, checkin, checkout):
    encoded_id = base64.b64encode(f"StayListing:{listing_id}".encode()).decode()
    
    body = {
        "operationName": "StaysPdpSections",
        "variables": {
            "id": encoded_id,
            "pdpSectionsRequest": {
                "adults": "1", "children": "0", "infants": "0", "pets": 0,
                "checkIn": checkin, "checkOut": checkout,
                "layouts": ["SIDEBAR", "SINGLE_COLUMN"],
                "privateBooking": False
            },
            "dateRange": {"startDate": checkin, "endDate": checkout},
            "guestCounts": {"numberOfAdults": 1, "numberOfChildren": 0, "numberOfInfants": 0, "numberOfPets": 0},
            "includeGpBookItFragment": True,
            "includeGpAmenitiesFragment": True,
            "includeGpReviewsFragment": True,
            "includeGpPoliciesFragment": True
        },
        "extensions": {
            "persistedQuery": {"version": 1, "sha256Hash": "3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d"}
        }
    }
    
    resp = requests.post(
        f"{BASE}/StaysPdpSections/3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d",
        headers=headers, json=body
    )
    return resp.json()

# Usage
data = get_listing_detail("129922792779005171", "2026-07-15", "2026-07-20")
```

## Example 3: Calendar (Needs Session Cookies)

```bash
curl -s -X POST \
  'https://www.airbnb.com/api/v3/PdpAvailabilityCalendar/be60714ead0a30db42ce6471ddad6a8f3855df0ed400b79282dd0bb8cecdf201' \
  -H 'Content-Type: application/json' \
  -H 'X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20' \
  -H 'User-Agent: Mozilla/5.0' \
  -d '{
    "operationName": "PdpAvailabilityCalendar",
    "variables": {"request": {"count": 3, "listingId": "12992279", "month": 7, "year": 2026}},
    "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "be60714ead0a30db42ce6471ddad6a8f3855df0ed400b79282dd0bb8cecdf201"}}
  }'
```

**Status:** ⚠️ Returns 403 without session cookies. Works with browser cookies.

## Known Issues
- **Domain:** Use `www.airbnb.com` (not `.com.sg` or other regional domains)
- **Calendar endpoint:** Needs authenticated session cookies
- **Reviews endpoint:** Variable names need to match exactly
- **Rate limiting:** ~1 request per 2-3 seconds per IP
