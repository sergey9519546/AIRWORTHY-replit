# Booking.com GraphQL — Cracked

> Endpoint: `https://www.booking.com/dml/graphql`
> Status: ✅ Working — Property cards with pricing, reviews, ratings

---

## Endpoint
```
POST https://www.booking.com/dml/graphql
```

## Response Structure

### Property Cards (69KB response)
```json
{
  "data": {
    "recommendationPlatform": {
      "propertyCards": {
        "cards": [
          {
            "id": 1075379,
            "translatedName": "Lloyd's Inn",
            "translatedPropertyType": "Hotel",
            "pageName": "lloyd-39-s-inn",
            "cc1": "sg",
            "ufi": -73635,
            "isGenius": false,
            "isPreferred": false,
            "ratingInfo": {
              "value": 3.0,
              "symbol": 0
            },
            "reviewInfo": {
              "reviewScore": 8.5,
              "reviewsCount": 943,
              "reviewTranslatedText": "Very good"
            },
            "locationInfo": {
              "translatedCityName": "Singapore",
              "translatedCountryName": "Singapore",
              "localizedDistanceFromCityCenter": "..."
            },
            "priceInfo": {
              "displayPrice": {
                "perStay": "..."
              },
              "priceBeforeDiscount": {
                "perStay": "..."
              }
            },
            "mainImage": {
              "urls": ["..."]
            }
          }
        ]
      }
    }
  }
}
```

## Data Available Per Property
| Field | Description |
|---|---|
| `id` | Booking.com property ID |
| `translatedName` | Property name |
| `translatedPropertyType` | Hotel, Apartment, etc. |
| `pageName` | URL slug |
| `cc1` | Country code |
| `ufi` | Unique facility identifier |
| `isGenius` | Genius member discount |
| `isPreferred` | Preferred partner status |
| `ratingInfo.value` | Star rating (1-5) |
| `reviewInfo.reviewScore` | Guest score (1-10) |
| `reviewInfo.reviewsCount` | Number of reviews |
| `reviewInfo.reviewTranslatedText` | Score text ("Very good", "Fabulous") |
| `locationInfo.translatedCityName` | City name |
| `locationInfo.translatedCountryName` | Country name |
| `priceInfo.displayPrice.perStay` | Displayed price |
| `priceInfo.priceBeforeDiscount.perStay` | Original price (before discount) |
| `mainImage.urls` | Image URLs |

## Other Endpoints Captured

| Size | Data |
|---|---|
| 155KB | Attraction cards (activities, tours) |
| 69KB | Property cards (hotels, apartments) |
| 18KB | Merch components (deals, promotions) |
| 14KB | Search acid carousel (featured properties) |
| 14KB | Weekend deals |

## Notes
- Results are NOT filtered to the searched city — appears to show global recommendations
- Need to filter by `locationInfo.translatedCityName` or `ufi`
- The `searchQueries.searchAcidCarousel` endpoint (14KB) may have more targeted results
- Need to capture the actual search results endpoint (not just recommendations)
