# Comp Set Algorithm — How Comps Work

> From AirDNA's OpenAPI spec + API behavior

---

## Comp Score (0-100)
Each comparable listing gets a `comp_score` indicating similarity to the target.

## Comp Selection Criteria (from API filters)

| Filter | Type | Description |
|---|---|---|
| accommodates | gte/lte/range/select | Guest count match |
| bedrooms | select | Bedroom count match |
| bathrooms | select | Bathroom count match |
| listing_type | select | entire_place / private_room / shared_room |
| property_type | select | Home, Apartment, etc. |
| amenities | 16 boolean flags | Amenity overlap |
| rating | gte | Rating threshold |
| review_count | gte | Review count threshold |
| superhost | boolean | Superhost filter |
| instant_book | boolean | Instant book filter |
| price_tier | select | Price tier match |
| professionally_managed | boolean | Management type |
| channels | multi_select | airbnb / vrbo / booking |

## Amenity Flags
```
has_aircon | has_breakfast | has_cable_tv | has_dryer | has_elevator |
has_gym | has_heating | has_hottub | has_kitchen | has_parking |
has_pets_allowed | has_pool | has_smoking | has_tv | has_washer |
has_wireless_internet
```

## Comp Search Methods

### By Listing ID
`POST /listing/{id}/comps` — Find comps for a specific listing

### By Radius
`POST /listing/comps/area` — Find comps within X meters of an address
- Sort by: proximity | revenue | adr | review_count
- Default radius: 1500m

## Comp Score Algorithm (Reconstructed)

```python
def calculate_comp_score(comp, target):
    score = 100
    
    # Geographic distance penalty
    distance = haversine(comp.location, target.location)
    score -= distance / 50  # -2 points per km
    
    # Bedroom match
    if comp.bedrooms != target.bedrooms:
        score -= 15
    
    # Bathroom match
    if comp.bathrooms != target.bathrooms:
        score -= 10
    
    # Accommodates match
    if comp.accommodates != target.accommodates:
        score -= 10
    
    # Property type match
    if comp.property_type != target.property_type:
        score -= 10
    
    # Listing type match
    if comp.listing_type != target.listing_type:
        score -= 15
    
    # Rating similarity
    rating_diff = abs(comp.rating - target.rating)
    score -= rating_diff * 5
    
    return max(0, min(100, score))
```

## Known Limitations
- New listings (zero reviews) significantly underperform estimates
- Thin markets with few comps produce unreliable estimates
- Dynamic pricing by hosts introduces variance not captured in trailing averages
- Mid/long-term stays (30+ nights) have different economics
- Cross-platform listing duplication can inflate supply counts
