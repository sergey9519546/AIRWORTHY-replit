# AirDNA Enterprise API Reference

> Full endpoint map from the OpenAPI spec (963KB, 27,793 lines)

---

## Base URL & Auth
```
Base: https://api.airdna.co/api/enterprise/v2/
Auth: Bearer <API_KEY> (sales-gated, no self-service)
```

## Market Data (10+ endpoints)
```
POST /market/search                    — Search by term or coordinates
GET  /market/{marketId}                — Market details
POST /country/{code}/markets           — Markets in country
POST /market/{id}/listings             — Listings in market
POST /market/{id}/submarkets           — Submarkets in market
POST /market/{id}/metrics/occupancy    — Occupancy (monthly, 12-60 months)
POST /market/{id}/metrics/avg_revenue  — Revenue with percentiles
POST /market/{id}/metrics/adr          — ADR with percentiles
POST /market/{id}/metrics/revpar       — RevPAR
POST /market/{id}/metrics/booking_lead_time — Lead time distribution
POST /market/{id}/metrics/avg_length_of_stay — Length of stay
POST /market/{id}/metrics/active_listings_count — Active listing counts
POST /market/{id}/future_pricing       — Future daily pricing (1-12 months)
```

## Submarket Data (9 endpoints)
```
POST /submarket/search                 — Search submarkets
GET  /submarket/{submarketId}          — Submarket details
POST /country/{code}/submarkets        — Explore submarkets
POST /market/{id}/submarkets           — Submarkets in market
POST /submarket/{id}/metrics/*         — Same metrics as market
POST /submarket/{id}/future_pricing    — Future daily pricing
```

## Listing Data (10 endpoints)
```
POST /market/search                    — Search listings
GET  /listing/{listingId}              — Full listing details
POST /listing/bulk/fetch               — Multiple listing details
POST /country/{code}/listings          — Listings by country
POST /market/{id}/listings             — Listings by market
POST /submarket/{id}/listings          — Listings by submarket
POST /listing/{id}/metrics             — Historical monthly metrics (12-60 months)
POST /listing/{id}/comps               — Comparable listings
POST /listing/comps/area               — Comps within radius
POST /listing/{id}/future/pricing      — Future daily pricing (1-12 months)
```

## Rentalizer (3 endpoints)
```
POST /rentalizer/estimate              — Detailed performance estimate
POST /rentalizer/summary/individual    — Summarized estimate
POST /rentalizer/bulk_summary          — Bulk estimates
```

## Smart Rates (2 endpoints)
```
GET  /listing/{id}/smart_rates/pricing_strategies — Base rates per strategy
POST /listing/{id}/smart_rates         — Daily recommended rates
```

## Filter System
Rich filtering with types: `select`, `multi_select`, `lt`, `lte`, `gt`, `gte`, `range`

**Market filters:** investability, listing count, market ID, market type, regulation, rental demand, revenue growth, seasonality

**Listing filters:** accommodates, amenities, bathrooms, bedrooms, channels, days available, instant book, listing type, occupancy rate, price tier, professionally managed, property type, ratings, real estate type, review count, superhost, percent active

## Rentalizer Request Schema
```json
{
  "address": "1321 15th St. Denver, CO 80202",
  "lat": 39.748847,
  "lng": -104.99891,
  "bedrooms": 3,
  "bathrooms": 3.5,
  "accommodates": 6,
  "currency": "usd"
}
```

## Rentalizer Response Schema
```json
{
  "details": {
    "address": "...",
    "zipcode": "80202",
    "accommodates": 6,
    "bedrooms": 3,
    "bathrooms": 3.5
  },
  "stats": {
    "currency": "usd",
    "property_value": 1234567,
    "future": {
      "summary": {
        "occupancy": 0.84,
        "adr": 436.45,
        "revenue": 11040,
        "revenue_lower": 10770,
        "revenue_upper": 11309
      },
      "metrics": [...]
    },
    "historical": {
      "summary": {
        "revenue_valuation": {
          "monthly_pct_change": -2.75,
          "yearly_pct_change": -2.62
        }
      },
      "metrics": [...]
    }
  },
  "comps": [
    {
      "property_id": "abnb_xxxxxxxx",
      "comp_score": 85,
      "details": {
        "title": "Downtown House w/ Private yard",
        "accommodates": 7,
        "bedrooms": 3,
        "bathrooms": 3,
        "reviews": 83,
        "rating": 4.9,
        "property_type": "Home",
        "listing_type": "entire_place"
      },
      "metrics": {
        "occupancy": 0.71,
        "days_available": 364,
        "days_reserved": 257,
        "adr": 272,
        "revenue": 69918
      }
    }
  ]
}
```

## GitHub Repos (AirDNA-related)
| Repo | Description |
|---|---|
| guestready/airdna-api | Python API client wrapper |
| jayesh2278/airdnascraper | Web scraper (old v1 API) |
| TimKahn/Guess_the_Address | Address prediction |
| spoliset80/propintel-app | Full-stack STR scanner |
