-- ============================================
-- InsideAirbnb Multi-Region Database Schema
-- SQLite3
-- Supports multiple states, cities, and snapshots.
-- ============================================

PRAGMA foreign_keys = ON;

-- Drop existing views and tables (for clean reload)
DROP VIEW IF EXISTS neighbourhood_summary;
DROP VIEW IF EXISTS listing_stats;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS listings;

-- ============================================
-- LISTINGS: One row per Airbnb listing per snapshot
-- ============================================
CREATE TABLE listings (
    id                          INTEGER,
    state                       TEXT NOT NULL,
    city                        TEXT NOT NULL,
    snapshot_date               TEXT NOT NULL,
    name                        TEXT,
    description                 TEXT,
    host_id                     INTEGER,
    host_name                   TEXT,
    host_since                  TEXT,
    host_is_superhost           INTEGER,
    host_listings_count         INTEGER,
    host_identity_verified      INTEGER,
    neighbourhood_cleansed      TEXT,
    neighbourhood_group_cleansed TEXT,
    latitude                    REAL,
    longitude                   REAL,
    property_type               TEXT,
    room_type                   TEXT,
    accommodates                INTEGER,
    bedrooms                    REAL,
    beds                        REAL,
    price                       TEXT,
    price_numeric               REAL,
    minimum_nights              INTEGER,
    maximum_nights              INTEGER,
    number_of_reviews           INTEGER,
    number_of_reviews_ltm       INTEGER,
    number_of_reviews_l30d      INTEGER,
    first_review                TEXT,
    last_review                 TEXT,
    review_scores_rating        REAL,
    review_scores_accuracy      REAL,
    review_scores_cleanliness   REAL,
    review_scores_checkin       REAL,
    review_scores_communication REAL,
    review_scores_location      REAL,
    review_scores_value         REAL,
    instant_bookable            INTEGER,
    calculated_host_listings_count INTEGER,
    availability_30             INTEGER,
    availability_60             INTEGER,
    availability_90             INTEGER,
    availability_365            INTEGER,
    estimated_occupancy_l365d   INTEGER,
    estimated_revenue_l365d     REAL,
    amenities                   TEXT,
    created_at                  TEXT DEFAULT (datetime('now')),
    updated_at                  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (id, state, city, snapshot_date)
);

-- ============================================
-- CALENDAR: Daily availability per listing per snapshot
-- ============================================
CREATE TABLE calendar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL,
    state           TEXT NOT NULL,
    city            TEXT NOT NULL,
    snapshot_date   TEXT NOT NULL,
    date            TEXT NOT NULL,
    available       INTEGER NOT NULL,
    minimum_nights  INTEGER,
    maximum_nights  INTEGER,
    FOREIGN KEY (listing_id, state, city, snapshot_date)
        REFERENCES listings(id, state, city, snapshot_date)
);

-- ============================================
-- REVIEWS: Individual guest reviews per snapshot
-- ============================================
CREATE TABLE reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL,
    state           TEXT NOT NULL,
    city            TEXT NOT NULL,
    snapshot_date   TEXT NOT NULL,
    date            TEXT NOT NULL,
    reviewer_id     INTEGER,
    reviewer_name   TEXT,
    comments        TEXT,
    FOREIGN KEY (listing_id, state, city, snapshot_date)
        REFERENCES listings(id, state, city, snapshot_date)
);

-- ============================================
-- INDEXES for performance
-- ============================================
CREATE INDEX idx_listings_state ON listings(state);
CREATE INDEX idx_listings_city ON listings(city);
CREATE INDEX idx_listings_snapshot ON listings(snapshot_date);
CREATE INDEX idx_listings_neighbourhood ON listings(neighbourhood_cleansed);
CREATE INDEX idx_listings_borough ON listings(neighbourhood_group_cleansed);
CREATE INDEX idx_listings_room_type ON listings(room_type);
CREATE INDEX idx_listings_host_id ON listings(host_id);
CREATE INDEX idx_listings_price ON listings(price_numeric);
CREATE INDEX idx_listings_reviews ON listings(number_of_reviews);
CREATE INDEX idx_listings_latitude ON listings(latitude);
CREATE INDEX idx_listings_longitude ON listings(longitude);
CREATE INDEX idx_listings_latlng ON listings(latitude, longitude);

CREATE INDEX idx_calendar_listing ON calendar(listing_id);
CREATE INDEX idx_calendar_state ON calendar(state);
CREATE INDEX idx_calendar_city ON calendar(city);
CREATE INDEX idx_calendar_snapshot ON calendar(snapshot_date);
CREATE INDEX idx_calendar_date ON calendar(date);
CREATE INDEX idx_calendar_available ON calendar(available);

CREATE INDEX idx_reviews_listing ON reviews(listing_id);
CREATE INDEX idx_reviews_state ON reviews(state);
CREATE INDEX idx_reviews_city ON reviews(city);
CREATE INDEX idx_reviews_snapshot ON reviews(snapshot_date);
CREATE INDEX idx_reviews_date ON reviews(date);

-- ============================================
-- VIEW: Pre-computed listing statistics
-- ============================================
CREATE VIEW listing_stats AS
SELECT
    l.id,
    l.state,
    l.city,
    l.snapshot_date,
    l.name,
    l.neighbourhood_cleansed AS neighbourhood,
    l.neighbourhood_group_cleansed AS borough,
    l.room_type,
    l.accommodates,
    l.bedrooms,
    l.price_numeric,
    l.number_of_reviews,
    l.review_scores_rating,
    l.availability_365,
    l.estimated_occupancy_l365d,
    l.estimated_revenue_l365d,
    l.host_id,
    l.host_listings_count,
    l.latitude,
    l.longitude,
    l.estimated_occupancy_l365d AS days_booked,
    l.availability_365 AS days_available,
    ROUND(100.0 * l.estimated_occupancy_l365d / 365, 1) AS occupancy_rate,
    l.estimated_revenue_l365d AS estimated_annual_revenue,
    CASE
        WHEN l.number_of_reviews_ltm > 0 THEN 'active'
        WHEN l.number_of_reviews > 0 THEN 'dormant'
        ELSE 'no_reviews'
    END AS listing_status
FROM listings l;

-- ============================================
-- VIEW: Neighborhood summary
-- ============================================
CREATE VIEW neighbourhood_summary AS
SELECT
    state,
    city,
    snapshot_date,
    borough,
    neighbourhood,
    COUNT(*) AS total_listings,
    ROUND(AVG(price_numeric), 2) AS avg_price,
    ROUND(AVG(review_scores_rating), 2) AS avg_rating,
    ROUND(AVG(availability_365), 0) AS avg_availability,
    ROUND(AVG(estimated_occupancy_l365d), 0) AS avg_occupancy,
    ROUND(AVG(estimated_revenue_l365d), 0) AS avg_revenue,
    SUM(number_of_reviews) AS total_reviews,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Entire home/apt' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_entire_home,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Private room' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_private_room,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Shared room' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_shared_room
FROM listings
WHERE price_numeric IS NOT NULL
GROUP BY state, city, snapshot_date, borough, neighbourhood;
