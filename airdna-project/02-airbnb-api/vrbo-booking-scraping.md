# Vrbo & Booking.com Scraping Approaches

> How to scrape the other two platforms AirDNA uses

---

## Booking.com — GraphQL API

Booking.com uses internal GraphQL endpoints for search results. Verified via HAR capture:

### Endpoint
```
POST https://www.booking.com/api/graphql
```

### Headers Required
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Content-Type': 'application/json',
    'X-Booking-Pageview-Id': 'unique_id_here',  # Dynamic session ID
}
```

### GraphQL Payload Structure
```json
{
    "operationName": "SearchQueries",
    "variables": {
        "input": {
            "dates": {
                "checkin": "2024-10-10",
                "checkout": "2024-10-15"
            },
            "location": {
                "destId": "something_for_paris",
                "destType": "CITY"
            },
            "nbAdults": 2,
            "nbChildren": 0,
            "nbRooms": 1,
            "pagination": {
                "rowsPerPage": 25,
                "offset": 0
            }
        }
    },
    "query": "query SearchQueries($input: SearchQueriesInput!) { ... }"
}
```

### Pagination
```python
results_list = []
current_offset = 0
total_results = 1
rows_per_page = 25

while current_offset < total_results:
    variables["input"]["pagination"]["offset"] = current_offset
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    
    search_data = data["data"]["searchQueries"]["search"]
    hotels = search_data["results"]
    results_list.extend(hotels)
    
    pagination_info = search_data["pagination"]
    total_results = pagination_info["nbResultsTotal"]
    
    current_offset += rows_per_page
```

### Response Structure
```
data.searchQueries.search.results[]
  .basicPropertyData.id
  .basicPropertyData.name
  .basicPropertyData.*
data.searchQueries.search.pagination.nbResultsTotal
data.searchQueries.search.pagination.offset
```

### Key Challenge
- `X-Booking-Pageview-Id` must be generated/captured per session
- GraphQL query string is massive — copy from DevTools
- Pagination is offset-based, not page-based

---

## Vrbo — Similar to Airbnb

Vrbo (owned by Expedia Group) uses a similar architecture to Airbnb:
- Server-side rendered pages with embedded JSON data
- Internal API endpoints behind anti-bot protection
- No public API for listing data

### Approach
1. **Browser automation** with stealth (same as Airbnb)
2. **HAR capture** to discover internal endpoints
3. **SSR JSON blob extraction** from page source

### Key Differences from Airbnb
- Different anti-bot system (not PerimeterX)
- Different URL structure
- Different GraphQL schema (if using GraphQL)
- Expedia Group API (if accessible)

### Data Available
- Listing details (title, description, amenities)
- Pricing (nightly rates, fees)
- Availability (calendar)
- Reviews
- Host information

---

## Cross-Platform Strategy

| Platform | Approach | Difficulty |
|---|---|---|
| **Airbnb** | Shadow API (cracked), SSR blob, browser | Medium |
| **Booking.com** | GraphQL API (capturable), browser | Medium-High |
| **Vrbo** | Browser automation, HAR capture | High |

### Unified Pipeline
1. Use Playwright with stealth for all three
2. Capture GraphQL/REST endpoints via network interception
3. Store in unified schema with platform-specific IDs
4. Cross-platform matching via GPS + photo hashing

---

## Tools for All Platforms

| Tool | Airbnb | Booking.com | Vrbo |
|---|---|---|---|
| **Playwright + stealth** | ✅ | ✅ | ✅ |
| **Shadow API (direct curl)** | ✅ | ⚠️ (GraphQL) | ❌ |
| **HAR capture** | ✅ | ✅ | ✅ |
| **SSR blob parsing** | ✅ (380KB) | ❌ | ❌ |
| **Scrapfly** | ✅ | ✅ | ✅ |
| **browse.sh** | ✅ (skill exists) | ❌ | ❌ |
