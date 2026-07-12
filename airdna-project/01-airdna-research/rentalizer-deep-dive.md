# Rentalizer Algorithm — Deep Technical Details

> From source code + HBS case study

---

## Request Parameters (Exactly 5)

```python
class RentalizerEstimateRequestSerializer(serializers.Serializer):
    accommodates = serializers.IntegerField()
    bathrooms = serializers.IntegerField()
    bedrooms = serializers.IntegerField()
    lat = serializers.CharField()
    lng = serializers.CharField()
```

**No amenity data, no property type, no review count, no photos.** The model infers everything from geographic comps.

## Response Structure

```json
{
  "details": {
    "address": "...",
    "address_lookup": "...",
    "zipcode": "...",
    "accommodates": 8,
    "bedrooms": 3,
    "bathrooms": 2
  },
  "location": { "lat": "40.7128", "lng": "-74.0060" },
  "stats": {
    "future": {
      "metrics": [
        {
          "adr": "250.00",
          "date": "2026-01",
          "occupancy": "0.55",
          "revenue": 4125,
          "revenue_lower": 3200,
          "revenue_upper": 5100
        }
      ],
      "summary": {
        "adr": "245.00",
        "occupancy": "0.52",
        "revenue": 46500
      }
    },
    "property_value": 450000.00
  }
}
```

## Key Insights

1. **Confidence intervals exist** — `revenue_lower` and `revenue_upper` are calculated but NOT prominently displayed in the UI
2. **Property valuation included** — `property_value` field suggests linked real estate valuation model
3. **Monthly granularity** — metrics provided per-month, enabling seasonal revenue curves
4. **ADR × Occupancy × Days = Revenue** — fundamental formula visible in response structure

## How It Actually Works (Reconstructed)

1. Takes lat/lng + property specs
2. Queries all active listings within geographic radius (10 miles)
3. Filters comps by bedroom count, bathroom count, accommodates
4. Pulls trailing 12-month performance data for comp set
5. Applies ML model to weight comps by recency, similarity, performance
6. Calculates monthly ADR, occupancy, revenue projections
7. Generates confidence intervals (lower/upper bounds)
8. Estimates property value (likely comparable sales + income approach)

## Comp Score (0-100)

Each comparable listing gets a `comp_score` indicating similarity to the target.

**Comp selection criteria (from API filters):**
```
accommodates, bedrooms, bathrooms, listing_type, property_type,
amenities, rating, reviews, superhost, instant_book, price_tier,
professionally_managed, channels
```

**Comp search methods:**
1. By Listing ID: `POST /listing/{id}/comps`
2. By Radius: `POST /listing/comps/area` (default radius: 1500m)

## Accuracy Issues (from Awning review)
- Estimates skew **optimistic** — reflect well-managed properties
- New listings with zero reviews will underperform
- Thin markets with few comps produce unreliable estimates
- Single outlier can skew projections in small comp sets
- Presented as single number in UI, giving false precision

## Source Code (guestready/airdna-api)

```python
class RentalizerEstimateResponseSerializer(serializers.Serializer):
    payload = PayloadSerializer(source="*")
    # Contains: details, location, stats.future.metrics[] (adr, date, occupancy, revenue, revenue_lower, revenue_upper)
    # stats.future.summary (adr, occupancy, revenue)
    # stats.property_value (optional decimal)
```
