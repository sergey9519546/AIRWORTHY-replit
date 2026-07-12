# Airbnb Shadow API Reference

> Cracked: 2026-06-28
> Method: Playwright CDP interception + direct GraphQL calls
> Status: **WORKING** — Full listing data, pricing, availability extracted

---

## API Key (Public, Embedded in Frontend)
```
X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20
```

## Endpoint Pattern
```
POST https://www.airbnb.com/api/v3/{OperationName}/{sha256Hash}
Content-Type: application/json
X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20
```

Airbnb uses **persisted queries** — operation name + SHA256 hash in URL. Server looks up query by hash.

## Core Data Operations

### StaysPdpSections (Listing Detail)
**Hash:** `3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d`

**Returns:**
- Pricing (discounted, original, per-night, breakdown)
- Availability (boolean)
- House rules (check-in/out, max guests)
- Cancellation policy
- Reviews summary
- Amenities
- Description
- Photos
- Location

**Variables:**
```json
{
  "id": "base64('StayListing:{listing_id}')",
  "pdpSectionsRequest": {
    "adults": "1", "children": "0", "infants": "0", "pets": 0,
    "checkIn": "2026-07-15", "checkOut": "2026-07-20",
    "layouts": ["SIDEBAR", "SINGLE_COLUMN"]
  },
  "dateRange": {"startDate": "2026-07-15", "endDate": "2026-07-20"},
  "guestCounts": {"numberOfAdults": 1, "numberOfChildren": 0, "numberOfInfants": 0, "numberOfPets": 0},
  "includeGpBookItFragment": true,
  "includeGpAmenitiesFragment": true,
  "includeGpReviewsFragment": true,
  "includeGpPoliciesFragment": true
}
```

### PdpAvailabilityCalendar (Calendar Data)
**Hash:** `be60714ead0a30db42ce6471ddad6a8f3855df0ed400b79282dd0bb8cecdf201`

**Returns:** Monthly calendar with daily availability, pricing, booking status

**Variables:**
```json
{
  "request": {
    "count": 3,
    "listingId": "12992279",
    "month": 7,
    "year": 2026
  }
}
```
**Note:** Requires session cookies for full access

### StaysPdpReviewsQuery (Reviews)
**Hash:** `bc9e4c87f9f06d8f5845bfe84c95365ee482b086397c4c8b7fb422c4c16e6d27`

**Returns:** Full review text, ratings, reviewer info

### SimilarListingsCarouselQuery (Comps)
**Hash:** `2dc877137f033bf448b2102fcd09da10d0325241f3ca9e8efc8d9acc4d3a699b`

**Returns:** Similar listings for comp analysis

### SearchInputQuery (Search)
**Hash:** `75d45a5e1c1158a9bde302c43871af604aec399b9344c9acef2ef87b9f974969`

**Returns:** Search autocomplete, location suggestions

## Working curl Example

```bash
curl -s -X POST \
  'https://www.airbnb.com/api/v3/StaysPdpSections/3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d' \
  -H 'Content-Type: application/json' \
  -H 'X-Airbnb-Api-Key: d306zoyjsyarp7ifhu67rjxn52tv0t20' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -H 'Accept: application/json' \
  -H 'Origin: https://www.airbnb.com' \
  -d '{...}' # Use exact variables from captured traffic
```

## Listing ID Encoding

Airbnb listing IDs must be base64-encoded:
```python
import base64
listing_id = "129922792779005171"
encoded = base64.b64encode(f"StayListing:{listing_id}".encode()).decode()
# Result: U3RheUxpc3Rpbmc6MTI5OTIyMjc5Mjc3OTAwNTE3MQ==
```

## Extracted Data Sample

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

## Discovered GraphQL Operations (14 total)

| Operation | Hash | Category |
|---|---|---|
| StaysPdpSections | `3b0949d0ae3b...` | Core Data |
| PdpAvailabilityCalendar | `be60714ead0a...` | Core Data |
| StaysPdpReviewsQuery | `bc9e4c87f9f0...` | Core Data |
| SimilarListingsCarouselQuery | `2dc877137f03...` | Core Data |
| StaysPdpBookItQuery | `a9a4a162092f...` | Core Data |
| SearchInputQuery | `75d45a5e1c11...` | Search |
| AutoSuggestionsQuery | `0d3d196304ca...` | Search |
| PlaceListingPolygonQuery | `037124258410...` | Geo |
| MapViewportInfoQuery | `aae2b4447f90...` | Geo |
| PlacesMapTileLayersQuery | `2801f85616c6...` | Geo |
| Header | `bb590cf8c21b...` | UI |
| NaviServerAnnouncementsQuery | `e37951ae03af...` | UI |
| GetConsentForUserQuery | `a3a01cb92f67...` | UI |
| GetConsentFlagsQuery | `ea4ccdd0346d...` | UI |
