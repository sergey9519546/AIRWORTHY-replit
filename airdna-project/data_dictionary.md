# 📖 Data Dictionary

Reference document for all fields in the InsideAirbnb NYC database.

## listings Table

Core listing data. One row per Airbnb listing.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Unique listing ID (primary key) | 2539 |
| name | TEXT | Listing title | "Clean & quiet apt near park" |
| description | TEXT | Full listing description | "Bright, serene room..." |
| host_id | INTEGER | Unique host ID | 2787 |
| host_name | TEXT | Host's display name | "John" |
| host_since | TEXT | Date host joined Airbnb | "2008-01-01" |
| host_is_superhost | INTEGER | 1 = superhost, 0 = not | 1 |
| host_listings_count | INTEGER | Number of listings this host has | 3 |
| host_identity_verified | INTEGER | 1 = verified, 0 = not | 1 |
| neighbourhood_cleansed | TEXT | Standardized neighborhood name | "Harlem" |
| neighbourhood_group_cleansed | TEXT | Borough name | "Manhattan" |
| latitude | REAL | Latitude coordinate | 40.64749 |
| longitude | REAL | Longitude coordinate | -73.97237 |
| property_type | TEXT | Type of property | "Entire rental unit" |
| room_type | TEXT | Room type category | "Entire home/apt" |
| accommodates | INTEGER | Maximum guests | 4 |
| bedrooms | REAL | Number of bedrooms | 1.0 |
| beds | REAL | Number of beds | 2.0 |
| price | TEXT | Original price string | "$113.97" |
| price_numeric | REAL | Parsed numeric price | 113.97 |
| minimum_nights | INTEGER | Minimum stay requirement | 30 |
| maximum_nights | INTEGER | Maximum stay allowed | 365 |
| number_of_reviews | INTEGER | Total reviews ever | 10 |
| number_of_reviews_ltm | INTEGER | Reviews in last 12 months | 5 |
| number_of_reviews_l30d | INTEGER | Reviews in last 30 days | 2 |
| first_review | TEXT | Date of first review | "2018-05-21" |
| last_review | TEXT | Date of most recent review | "2024-11-15" |
| review_scores_rating | REAL | Overall rating (0-5) | 4.8 |
| review_scores_accuracy | REAL | Accuracy score (0-5) | 4.9 |
| review_scores_cleanliness | REAL | Cleanliness score (0-5) | 4.7 |
| review_scores_checkin | REAL | Check-in score (0-5) | 5.0 |
| review_scores_communication | REAL | Communication score (0-5) | 4.8 |
| review_scores_location | REAL | Location score (0-5) | 4.5 |
| review_scores_value | REAL | Value score (0-5) | 4.6 |
| instant_bookable | INTEGER | 1 = can book instantly, 0 = requires approval | 0 |
| calculated_host_listings_count | INTEGER | Total listings by this host | 3 |
| availability_30 | INTEGER | Days available in next 30 days | 15 |
| availability_60 | INTEGER | Days available in next 60 days | 30 |
| availability_90 | INTEGER | Days available in next 90 days | 45 |
| availability_365 | INTEGER | Days available in next 365 days | 339 |
| estimated_occupancy_l365d | INTEGER | Pre-calculated: estimated booked days in last 365 days | 60 |
| estimated_revenue_l365d | REAL | Pre-calculated: estimated revenue in last 365 days ($) | 6838.0 |
| amenities | TEXT | JSON array of amenities | '["Wifi","Kitchen",...]' |
| created_at | TEXT | Record creation timestamp | Auto-generated |
| updated_at | TEXT | Record update timestamp | Auto-generated |

## calendar Table

Daily availability data. One row per listing per day.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Auto-increment primary key | 1 |
| listing_id | INTEGER | Links to listings.id | 2539 |
| date | TEXT | Date (YYYY-MM-DD) | "2026-06-14" |
| available | INTEGER | 1 = available, 0 = booked | 1 |
| minimum_nights | INTEGER | Minimum stay for this date | 30 |
| maximum_nights | INTEGER | Maximum stay for this date | 365 |

**Note:** This calendar dataset does NOT include price data. Use `listings.price_numeric` for pricing.

## reviews Table

Individual guest reviews. One row per review.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Auto-increment primary key | 1 |
| listing_id | INTEGER | Links to listings.id | 2539 |
| date | TEXT | Review date (YYYY-MM-DD) | "2024-11-15" |
| reviewer_id | INTEGER | Unique reviewer ID | 456789 |
| reviewer_name | TEXT | Reviewer's display name | "Alice" |
| comments | TEXT | Review text | "Great place, very clean..." |

## Pre-computed Views

### listing_stats

Aggregated view joining listings with calendar-derived statistics.

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Listing ID |
| name | TEXT | Listing title |
| neighbourhood | TEXT | Neighborhood name |
| borough | TEXT | Borough name |
| room_type | TEXT | Room type |
| accommodates INTEGER | Max guests |
| bedrooms | REAL | Number of bedrooms |
| price_numeric | REAL | Nightly price |
| number_of_reviews | INTEGER | Total reviews |
| review_scores_rating | REAL | Overall rating |
| availability_365 | INTEGER | Days available next year |
| estimated_occupancy_l365d | INTEGER | Estimated booked days |
| estimated_revenue_l365d | REAL | Estimated annual revenue |
| host_id | INTEGER | Host ID |
| host_listings_count | INTEGER | Host's listing count |
| latitude | REAL | Latitude |
| longitude | REAL | Longitude |
| days_booked | INTEGER | Same as estimated_occupancy_l365d |
| days_available | INTEGER | Same as availability_365 |
| occupancy_rate | REAL | Percentage of year booked |
| estimated_annual_revenue | REAL | Same as estimated_revenue_l365d |
| listing_status | TEXT | 'active', 'dormant', or 'no_reviews' |

### neighbourhood_summary

Aggregated statistics by neighborhood.

| Field | Type | Description |
|-------|------|-------------|
| borough | TEXT | Borough name |
| neighbourhood | TEXT | Neighborhood name |
| total_listings | INTEGER | Number of listings |
| avg_price | REAL | Average nightly price |
| avg_rating | REAL | Average review score |
| avg_availability | REAL | Average days available |
| avg_occupancy | REAL | Average days booked |
| avg_revenue | REAL | Average estimated revenue |
| total_reviews | INTEGER | Total reviews in neighborhood |
| pct_entire_home | REAL | % that are entire home rentals |
| pct_private_room | REAL | % that are private rooms |
| pct_shared_room | REAL | % that are shared rooms |

## Key Business Terms

- **Occupancy Rate:** Percentage of the year a listing is booked
- **Ghost Listing:** Listing with 0 reviews in last 12 months AND high availability (>300 days) — likely inactive
- **Host Concentration:** How much of the market is controlled by hosts with many listings
- **Superhost:** Airbnb's badge for experienced, high-rated hosts
- **Instant Bookable:** Can be booked without host approval

## Common Queries

See `notebooks/02_tier0_starter.ipynb` for example queries using this schema.
