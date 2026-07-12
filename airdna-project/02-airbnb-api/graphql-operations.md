# Airbnb GraphQL Operations — Complete Reference

> All 14 discovered operations with hashes, variables, and response structures

---

## How It Works
Airbnb uses **persisted queries** — the operation name + SHA256 hash are in the URL. The server looks up the query by hash; you don't send the GraphQL query itself.

```
POST https://www.airbnb.com/api/v3/{OperationName}/{sha256Hash}
```

## Core Data Operations

### StaysPdpSections (Listing Detail)
**Hash:** `3b0949d0ae3b4a4e6a1719f00901e031b7cdc13f4263e35b92d517856df2dd4d`
**Returns:** Pricing, availability, house rules, cancellation policy, reviews summary, amenities, description, photos, location

**Key Variables:**
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

**Response Structure:**
```
data.presentation.stayProductDetailPage.sections.sections[]
  ├── BOOK_IT_SIDEBAR → pricing, availability, max guests
  ├── POLICIES_DEFAULT → house rules, cancellation policy
  ├── BOOK_IT_NAV → booking navigation
  ├── BOOK_IT_FLOATING_FOOTER → floating book button
  ├── BOOK_IT_CALENDAR_SHEET → calendar sheet
  └── CANCELLATION_POLICY_PICKER_MODAL → cancellation options
```

### PdpAvailabilityCalendar (Calendar Data)
**Hash:** `be60714ead0a30db42ce6471ddad6a8f3855df0ed400b79282dd0bb8cecdf201`
**Returns:** Monthly calendar with daily availability, pricing, booking status
**Note:** Requires session cookies for full access

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

### StaysPdpReviewsQuery (Reviews)
**Hash:** `bc9e4c87f9f06d8f5845bfe84c95365ee482b086397c4c8b7fb422c4c16e6d27`
**Returns:** Full review text, ratings, reviewer info

### SimilarListingsCarouselQuery (Comps)
**Hash:** `2dc877137f033bf448b2102fcd09da10d0325241f3ca9e8efc8d9acc4d3a699b`
**Returns:** Similar listings for comp analysis

### StaysPdpBookItQuery (Booking Info)
**Hash:** `a9a4a162092fa4d070bcc6e720e47eb1066621a2c70c65d1c816a361245f4769`
**Returns:** Rate plans, pricing tiers

## Search Operations

### SearchInputQuery
**Hash:** `75d45a5e1c1158a9bde302c43871af604aec399b9344c9acef2ef87b9f974969`
**Returns:** Search autocomplete, location suggestions

### AutoSuggestionsQuery
**Hash:** `0d3d196304ca7be3b077e90e5962ec64b82026b3e9d2f9b7422b58ac02feed9c`
**Returns:** Location autocomplete

## Geo Operations

### PlaceListingPolygonQuery
**Hash:** `0371242584102831acce5ae21f6c68547fba8c0f13ae5643f1fd9b8205d4ba6f`
**Returns:** Geographic boundaries

### MapViewportInfoQuery
**Hash:** `aae2b4447f90adfd800a006f1afc80e2df9f98ddc8cd932628da179ebae10c79`
**Returns:** Map viewport metadata

### PlacesMapTileLayersQuery
**Hash:** `2801f85616c647da897107111266a31b9eb408f109250b54f442b9c6ca781b93`
**Returns:** Map tile data

## UI Operations

### Header
**Hash:** `bb590cf8c21b62e4b5122e1cd19969f1f1df72832040a335fd45af52597440e4`
**Returns:** Navigation header, user state

### NaviServerAnnouncementsQuery
**Hash:** `e37951ae03af6a7d0ee7c059c0b9bf17ac3181b3a86cff069babe361ae84108a`
**Returns:** Server announcements

### GetConsentForUserQuery
**Hash:** `a3a01cb92f67abf3565887799a72523309c26de8f351553e7976b2fb0b2d074d`
**Returns:** Cookie consent state

### GetConsentFlagsQuery
**Hash:** `ea4ccdd0346dfc6f8e581e6686615cfd79d530e9cfb7df266e841f990ec6ff3e`
**Returns:** Consent feature flags

## Listing ID Encoding
```python
import base64
listing_id = "129922792779005171"
encoded = base64.b64encode(f"StayListing:{listing_id}".encode()).decode()
# → U3RheUxpc3Rpbmc6MTI5OTIyMjc5Mjc3OTAwNTE3MQ==
```
