# Filter System — Complete Reference

> All listing and market filters from AirDNA's API

---

## Listing Filters

| Filter | Type | Values |
|---|---|---|
| accommodates | gte/lte/range/select | Guest count (1-16+) |
| bedrooms | select | Studio, 1-6+ |
| bathrooms | select | 1-6+ |
| listing_type | select | entire_place, private_room, shared_room |
| property_type | select | Home, Apartment, Condo, etc. |
| amenities | 16 boolean flags | See below |
| channels | multi_select | airbnb, vrbo, booking |
| instant_book | boolean | true/false |
| superhost | boolean | true/false |
| rating | gte | 0-5 |
| review_count | gte | Number of reviews |
| price_tier | select | Budget, Mid-range, Luxury |
| professionally_managed | boolean | true/false |
| occupancy_rate_ltm | gte/lte | 0-1 (trailing 12 months) |
| days_available_ltm | gte/lte | Days available |
| days_reserved_ltm | gte/lte | Days reserved |
| revenue_ltm | gte/lte | Revenue amount |
| adr_ltm | gte/lte | Average daily rate |

## Amenity Flags (16)
```
has_aircon | has_breakfast | has_cable_tv | has_dryer | has_elevator |
has_gym | has_heating | has_hottub | has_kitchen | has_parking |
has_pets_allowed | has_pool | has_smoking | has_tv | has_washer |
has_wireless_internet
```

## Market Filters

| Filter | Type | Values |
|---|---|---|
| investability | gte/lte | 0-100 score |
| listing_count | gte/lte | Active listing count |
| market_id | select | Specific market |
| market_type | select | urban_metro, coastal, mountains_lakes, suburban, rural, mid_size_city |
| regulation | gte/lte | 0-100 score |
| rental_demand | gte/lte | 0-100 score |
| revenue_growth | gte/lte | 0-100 score |
| seasonality | gte/lte | 0-100 score |

## Filter Types
```
select       — Single value from list
multi_select — Multiple values from list
lt           — Less than
lte          — Less than or equal
gt           — Greater than
gte          — Greater than or equal
range        — Min/max range
```

## Sort Options
```
proximity    — Distance from target
revenue      — Revenue (high to low)
adr          — Average daily rate
review_count — Number of reviews
occupancy    — Occupancy rate
rating       — Guest rating
```
