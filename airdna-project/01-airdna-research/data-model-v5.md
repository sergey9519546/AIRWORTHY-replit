# AirDNA Data Model 5.0

> The 5 sub-models that power AirDNA's analytics

---

## Evolution
- **2015 — Model 1.0:** Industry's first STR reservation model
- **2018 — Model 2.0:** Introduced Vrbo and cross-platform matching
- **2019 — Model 3.0:** Rebuilt for major Airbnb API changes
- **2023 — Model 4.0:** Updated for Airbnb's date-selection pricing change
- **2025 — Model 5.0:** Five sub-models, 2x accuracy for mid/long-term stays

## The 5 Sub-Models

### 1. Analyzation Model
- Decides the most accurate metrics daily
- Handles conflicting data from multiple scrapes per day
- Selects best representation of each metric

### 2. Matching Model
- Cross-platform deduplication
- Uses **14 metrics**: location, title, description, bedrooms, calendar availability, etc.
- Matches same property across Airbnb + Vrbo + Booking.com
- Removes duplicate data

### 3. Reservation Model (THE SECRET)
- Detects true bookings vs host-blocked days
- Uses **16 different booking signals** with AI/ML
- Signals include: length of stay, lead times, reviews, calendar patterns
- **We reverse-engineered PriceLabs' version of this**

### 4. Pricing Model
- Updated in 2023 for Airbnb's date-gated pricing
- Requires date-by-date scraping
- Handles dynamic pricing detection

### 5. Anomaly Detection Model
- Filters outlier data
- Removes fake/inactive listings
- Quality scoring
- Stronger in Model 5.0

## What AirDNA Tracks Per Listing

### Core Fields
```
property_id          — AirDNA ID (abnb_*, vrbo_*, bkng_*)
airbnb_property_id   — Airbnb listing ID
vrbo_property_id     — Vrbo listing ID
booking_property_id  — Booking.com ID
title, market_name, accommodates, bedrooms, bathrooms
reviews, rating, property_type, listing_type
superhost, instant_book, cancellation_policy
created_date, license, cleaning_fee
```

### Performance Metrics (Trailing 12 Months)
```
occupancy, adr, revenue, revenue_potential
days_available, days_blocked, days_reserved
num_reservations, response_rate, response_time
last_calendar_update, last_scraped_date
```

### Ratings (Airbnb-specific)
```
overall, accuracy, checkin, cleanliness, communication, location, value
```

### Location
```
lat, lng, country, city, state, zipcode, msa
```

## Occupancy Calculation
AirDNA only counts "active listing nights":
- Nights that are not blocked
- Either reserved or available
- Provided there has been a reservation within the past 28 days

## Deduplication Algorithm
Uses 14 metrics to match properties across OTAs:
1. Geographic coordinates
2. Title similarity
3. Description similarity
4. Bedroom count
5. Bathroom count
6. Guest capacity
7. Property type
8. Room type
9. Calendar availability pattern
10. Photo similarity
11. Amenity overlap
12. Host information
13. Review patterns
14. Price range

## Data Sources
1. **Web Scraping** — Airbnb, Vrbo, Booking.com daily
2. **Partner Data** — Property managers, channel managers
3. **Individual Hosts** — Direct data contribution

## Scale
- 10M+ properties tracked
- 120K+ markets globally
- 1.3M+ users since 2015
- 10+ years of historical data

## Academic Validation
- Widely used in academic research (NIH/PMC papers)
- MIT Sloan paper used AirDNA for tax compliance analysis
- ProQuest study identifies AirDNA as one of three major STR data sources

## Patents
**None found.** AirDNA's moat is:
- Proprietary data accumulation (10+ years)
- ML model refinement (5 iterations)
- Network effects and institutional adoption
- Brand recognition as industry standard
