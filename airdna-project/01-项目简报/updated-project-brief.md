# 🏠 InsideAirbnb × 青旅选址 — Updated Project Brief
## For Beginners: From Zero to Data Analyst in 8 Weeks

---

## 📍 You Are Here

You have **705 MB of real Airbnb data** (50,281 listings, 2.4M calendar records, 1.3M reviews) from InsideAirbnb for New York City. This data was collected using the methodology at insideairbnb.com.

Your mission: **Analyze this data to determine which NYC neighborhoods are best suited for opening a new youth hostel (青旅).**

This brief will guide you step-by-step. You don't need to figure anything out from scratch — follow the curriculum, use the starter code, and build your skills progressively.

---

## 🗂️ What You Have (Data Inventory)

### Files in `raw data/`

| File | Size | Records | What It Contains |
|------|------|---------|------------------|
| `listings.csv.gz` | 24 MB | 50,281 | One row per Airbnb listing — price, location, reviews, host info, room type, amenities |
| `calendar.csv.gz` | 323 MB | 2,403,455 | Daily availability & price for each listing (next 365 days) |
| `reviews.csv.gz` | 358 MB | 1,330,657 | Individual guest reviews with dates and text |

### Key Data Fields You'll Use

**listings.csv** — The core dataset. Important columns:
- `id` — Unique listing ID
- `name`, `description` — Listing title and description
- `host_id`, `host_name`, `host_since` — Host info
- `neighbourhood_cleansed` — Neighborhood name (standardized)
- `neighbourhood_group_cleansed` — Borough (Manhattan, Brooklyn, etc.)
- `latitude`, `longitude` — Exact location
- `room_type` — "Entire home/apt", "Private room", "Shared room", "Hotel room"
- `accommodates` — How many guests
- `bedrooms`, `bathrooms` — Size
- `price` — Nightly price (as string like "$150.00")
- `minimum_nights`, `maximum_nights` — Stay requirements
- `number_of_reviews`, `first_review`, `last_review` — Review history
- `review_scores_rating` — Overall rating (0-5)
- `availability_365` — Days available in next year
- `instant_bookable` — Can book without host approval
- `calculated_host_listings_count` — How many listings this host has
- `amenities` — JSON-like list of amenities (WiFi, kitchen, etc.)
- `estimated_occupancy_l365d` — **Pre-calculated:** Estimated booked days in last 365 days
- `estimated_revenue_l365d` — **Pre-calculated:** Estimated revenue in last 365 days ($)

**calendar.csv** — Daily pricing & availability:
- `listing_id` — Links to listings.id
- `date` — Date (YYYY-MM-DD)
- `available` — "t" (available) or "f" (booked)
- `minimum_nights` — Minimum stay for this date
- `maximum_nights` — Maximum stay for this date

**⚠️ IMPORTANT:** This calendar has NO price column! Use `listings.price` and `listings.estimated_revenue_l365d` instead.

**reviews.csv** — Guest reviews:
- `listing_id` — Links to listings.id
- `date` — Review date
- `comments` — Review text

---

## 🎯 What You're Building (The Four Tiers)

Think of this as a video game with four levels. You MUST complete each tier before moving to the next.

### Tier 0: Data Audit & Database Setup ⭐
**Goal:** Load raw CSVs into a proper database and verify data quality.
**Time:** Days 1-3
**Skills:** SQL basics, data loading, data validation

**What you'll do:**
1. Create a SQLite database with a proper schema (provided below)
2. Write a Python script to load the CSVs into the database
3. Run validation queries to answer: "What do we actually have?"
4. Document data quality issues

**Concrete deliverable:** A Jupyter notebook or Python script that:
- Loads all data into SQLite
- Prints summary statistics (counts, date ranges, missing values)
- Answers these specific questions:
  - How many listings are there per borough?
  - What's the date range of the reviews?
  - What percentage of listings have zero reviews?
  - What are the room type distributions?
  - Are there any duplicate listing IDs?

**Validation checkpoint:** Your database should have:
- `listings` table: 50,281 rows
- `calendar` table: ~2.4M rows
- `reviews` table: ~1.3M rows
- No duplicate listing IDs
- All prices parseable as numbers

---

### Tier 1: Market Overview (Can we compete?) ⭐⭐
**Goal:** Understand the competitive landscape and identify which boroughs/neighborhoods have the most opportunity.
**Time:** Days 4-8
**Skills:** SQL aggregations, pandas groupby, matplotlib basics, bar charts

**What you'll do:**
1. Calculate revenue estimates from calendar data
2. Analyze pricing by borough and room type
3. Identify market saturation (supply vs. demand)
4. Create visualizations for each question

**Concrete deliverable:** Answer these questions with charts and numbers:

1. **Borough comparison:**
   - Average nightly price by borough (bar chart)
   - Number of listings by borough (bar chart)
   - Average occupancy rate by borough (bar chart)

2. **Room type analysis:**
   - Distribution of room types (pie chart)
   - Average price by room type (bar chart)
   - Which room type has highest occupancy?

3. **Revenue estimates:**
   - Top 10 neighborhoods by estimated annual revenue (use `estimated_revenue_l365d`)
   - Revenue distribution histogram
   - Average revenue by borough

**Validation checkpoint:**
- You should be able to explain: "In [borough], the average nightly rate is $X, with Y% occupancy, generating $Z estimated annual revenue."
- You should have at least 6 charts (2 per question)

---

### Tier 2: Location Scoring (Where should we open?) ⭐⭐⭐
**Goal:** Build a scoring system to rank neighborhoods for hostel viability.
**Time:** Days 9-14
**Skills:** Feature engineering, scoring algorithms, advanced SQL, seaborn heatmaps

**What you'll do:**
1. Identify "ghost listings" (inactive listings that inflate supply)
2. Calculate host concentration (are there mega-hosts dominating?)
3. Analyze seasonal patterns in pricing and occupancy
4. Build a composite scoring model

**Concrete deliverable:** A neighborhood scorecard with:

1. **Ghost listing analysis:**
   - Define criteria for "ghost" (e.g., 0 reviews in last 12 months, availability > 300 days)
   - Calculate ghost rate by neighborhood
   - Adjusted supply (total listings minus ghosts)

2. **Host concentration:**
   - Top 10 hosts by number of listings
   - Market share of top 5% of hosts by borough
   - Is the market dominated by mega-hosts or distributed?

3. **Seasonal patterns:**
   - Monthly occupancy rate (line chart)
   - Monthly price trends (line chart)
   - Best/worst months for revenue

4. **Composite score:**
   - Score = w1×(market_size) + w2×(avg_revenue) + w3×(1-ghost_rate) + w4×(1-concentration)
   - Rank all neighborhoods by score
   - Top 5 recommended neighborhoods with explanation

**Validation checkpoint:**
- You should have a ranked list of neighborhoods with scores
- You should be able to explain WHY each neighborhood scored high or low
- You should have identified at least one "hidden gem" (high potential, low competition)

---

### Tier 3: Deep Analysis & Dashboard ⭐⭐⭐⭐
**Goal:** Build predictive models and an interactive dashboard.
**Time:** Days 15-28
**Skills:** scikit-learn basics, NLP fundamentals, Streamlit/Dash, interactive visualizations

**What you'll do:**
1. Build a price prediction model (what drives pricing?)
2. Analyze guest reviews with NLP (what do guests care about?)
3. Analyze amenity impact on pricing
4. Build an interactive dashboard

**Concrete deliverable:**

1. **Price prediction model:**
   - Features: location, room type, accommodates, amenities, reviews, etc.
   - Model: Linear Regression or Random Forest
   - Evaluation: R² score, MAE
   - Feature importance ranking (what drives price?)

2. **Amenity analysis:**
   - Parse amenities from listings
   - Calculate price premium for each amenity
   - Top 10 amenities that increase price the most
   - Recommended amenity package for hostel

3. **Review NLP (bonus):**
   - Word cloud of positive vs. negative reviews
   - Common complaints and praises
   - What do guests value most?

4. **Interactive dashboard:**
   - Map of NYC with listings (colored by price or rating)
   - Filters by borough, room type, price range
   - Neighborhood comparison charts
   - Revenue calculator (input: location + rooms → estimated revenue)

---

## 🗄️ Database Design (The Foundation)

This is the most important part of the project. A good database makes everything else easy.

### Schema: `schema.sql`

```sql
-- ============================================
-- InsideAirbnb NYC Database Schema
-- SQLite3
-- ============================================

-- Drop existing tables (for clean reload)
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS listings;

-- ============================================
-- LISTINGS: One row per Airbnb listing
-- ============================================
CREATE TABLE listings (
    id                          INTEGER PRIMARY KEY,
    name                        TEXT,
    description                 TEXT,
    host_id                     INTEGER,
    host_name                   TEXT,
    host_since                  TEXT,          -- Date string YYYY-MM-DD
    host_is_superhost           INTEGER,       -- 1 = yes, 0 = no
    host_listings_count         INTEGER,       -- How many listings this host has
    host_identity_verified      INTEGER,       -- 1 = yes, 0 = no
    neighbourhood_cleansed      TEXT,          -- Standardized neighborhood name
    neighbourhood_group_cleansed TEXT,         -- Borough (Manhattan, Brooklyn, etc.)
    latitude                    REAL,
    longitude                   REAL,
    property_type               TEXT,          -- Apartment, House, etc.
    room_type                   TEXT,          -- Entire home, Private room, Shared room, Hotel room
    accommodates                INTEGER,       -- Max guests
    bedrooms                    REAL,          -- Number of bedrooms
    beds                        REAL,          -- Number of beds
    price                       TEXT,          -- Original string price (e.g., "$150.00")
    price_numeric               REAL,          -- Parsed numeric price (you'll calculate this)
    minimum_nights              INTEGER,
    maximum_nights              INTEGER,
    number_of_reviews           INTEGER,
    number_of_reviews_ltm       INTEGER,       -- Reviews in last 12 months
    number_of_reviews_l30d      INTEGER,       -- Reviews in last 30 days
    first_review                TEXT,          -- Date of first review
    last_review                 TEXT,          -- Date of most recent review
    review_scores_rating        REAL,          -- Overall rating (0-5)
    review_scores_accuracy      REAL,
    review_scores_cleanliness   REAL,
    review_scores_checkin       REAL,
    review_scores_communication REAL,
    review_scores_location      REAL,
    review_scores_value         REAL,
    instant_bookable            INTEGER,       -- 1 = yes, 0 = no
    calculated_host_listings_count INTEGER,
    availability_30             INTEGER,       -- Days available in next 30 days
    availability_60             INTEGER,
    availability_90             INTEGER,
    availability_365            INTEGER,       -- Days available in next year
    amenities                   TEXT,          -- JSON array string
    created_at                  TEXT DEFAULT (datetime('now')),
    updated_at                  TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- CALENDAR: Daily availability & price per listing
-- ============================================
CREATE TABLE calendar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,          -- YYYY-MM-DD
    available       INTEGER NOT NULL,       -- 1 = available, 0 = booked
    price           TEXT,                   -- Original string price
    price_numeric   REAL,                   -- Parsed numeric price
    FOREIGN KEY (listing_id) REFERENCES listings(id)
);

-- ============================================
-- REVIEWS: Individual guest reviews
-- ============================================
CREATE TABLE reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,          -- YYYY-MM-DD
    reviewer_id     INTEGER,
    reviewer_name   TEXT,
    comments        TEXT,
    FOREIGN KEY (listing_id) REFERENCES listings(id)
);

-- ============================================
-- INDEXES for performance
-- ============================================
CREATE INDEX idx_listings_neighbourhood ON listings(neighbourhood_cleansed);
CREATE INDEX idx_listings_borough ON listings(neighbourhood_group_cleansed);
CREATE INDEX idx_listings_room_type ON listings(room_type);
CREATE INDEX idx_listings_host_id ON listings(host_id);
CREATE INDEX idx_listings_price ON listings(price_numeric);
CREATE INDEX idx_listings_reviews ON listings(number_of_reviews);

CREATE INDEX idx_calendar_listing ON calendar(listing_id);
CREATE INDEX idx_calendar_date ON calendar(date);
CREATE INDEX idx_calendar_available ON calendar(available);

CREATE INDEX idx_reviews_listing ON reviews(listing_id);
CREATE INDEX idx_reviews_date ON reviews(date);

-- ============================================
-- VIEW: Pre-computed listing statistics (saves you work later!)
-- ============================================
CREATE VIEW listing_stats AS
SELECT
    l.id,
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
    l.host_id,
    l.host_listings_count,
    l.latitude,
    l.longitude,
    -- Calendar-derived stats
    cal.total_days_listed,
    cal.days_available,
    cal.days_booked,
    cal.avg_price,
    cal.min_price,
    cal.max_price,
    ROUND(100.0 * cal.days_booked / cal.total_days_listed, 1) AS occupancy_rate,
    -- Estimated annual revenue
    ROUND(cal.avg_price * cal.days_booked, 0) AS estimated_annual_revenue,
    -- Review activity
    CASE
        WHEN l.number_of_reviews_ltm > 0 THEN 'active'
        WHEN l.number_of_reviews > 0 THEN 'dormant'
        ELSE 'no_reviews'
    END AS listing_status
FROM listings l
LEFT JOIN (
    SELECT
        listing_id,
        COUNT(*) AS total_days_listed,
        SUM(CASE WHEN available = 1 THEN 1 ELSE 0 END) AS days_available,
        SUM(CASE WHEN available = 0 THEN 1 ELSE 0 END) AS days_booked,
        ROUND(AVG(price_numeric), 2) AS avg_price,
        MIN(price_numeric) AS min_price,
        MAX(price_numeric) AS max_price
    FROM calendar
    WHERE price_numeric IS NOT NULL
    GROUP BY listing_id
) cal ON l.id = cal.listing_id;

-- ============================================
-- VIEW: Neighborhood summary (pre-computed for Tier 1)
-- ============================================
CREATE VIEW neighbourhood_summary AS
SELECT
    borough,
    neighbourhood,
    COUNT(*) AS total_listings,
    ROUND(AVG(price_numeric), 2) AS avg_price,
    ROUND(AVG(review_scores_rating), 2) AS avg_rating,
    ROUND(AVG(availability_365), 0) AS avg_availability,
    SUM(number_of_reviews) AS total_reviews,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Entire home/apt' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_entire_home,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Private room' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_private_room,
    ROUND(100.0 * SUM(CASE WHEN room_type = 'Shared room' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_shared_room
FROM listings
WHERE price_numeric IS NOT NULL
GROUP BY borough, neighbourhood;
```

### Why This Schema?

**Why SQLite?**
- Zero setup — it's just a file
- Works on Windows, Mac, Linux
- Python has built-in support
- Handles millions of rows easily
- You can query it with any SQL tool

**Why not normalize further?**
- You're beginners — a simpler schema is easier to understand
- SQLite handles wide tables well
- Fewer JOINs = simpler queries
- You can always create views for complex analysis

**Why the views?**
- `listing_stats` pre-calculates occupancy and revenue from calendar data
- `neighbourhood_summary` gives you Tier 1 answers with one `SELECT *`
- Views save you from writing complex JOINs every time

**Why keep both string and numeric prices?**
- Original data has prices as strings ("$150.00")
- You need to parse them — keeping both lets you verify your parsing
- The numeric column is what you'll actually use for calculations

---

## 📚 Skill-Building Curriculum (8 Weeks)

### Week 1: Foundation + Tier 0 (Days 1-7)
**Goal:** Set up your environment, load data, complete Tier 0

#### Day 1: Environment Setup
**Morning:**
- Install Python 3.10+ (if not already installed)
- Install VS Code or JupyterLab
- Create a virtual environment:
  ```bash
  python -m venv airbnb-env
  # Windows:
  airbnb-env\Scripts\activate
  # Mac/Linux:
  source airbnb-env/bin/activate
  ```
- Install required packages:
  ```bash
  pip install pandas numpy matplotlib seaborn jupyter sqlite3
  ```
- Create project folder structure:
  ```
  airbnb-project/
  ├── data/
  │   └── raw/          ← Put the 3 CSV files here
  ├── db/
  │   └── airbnb.db     ← SQLite database (will be created)
  ├── notebooks/
  │   ├── 01_data_loading.ipynb
  │   ├── 02_tier0_audit.ipynb
  │   └── ...
  ├── scripts/
  │   ├── create_database.py
  │   ├── load_data.py
  │   └── ...
  ├── output/
  │   ├── charts/
  │   └── reports/
  ├── schema.sql
  └── requirements.txt
  ```

**Afternoon:**
- Read the InsideAirbnb methodology: https://insideairbnb.com/get-the-data/
- Open the raw CSVs in a text editor and explore the first few rows
- Identify which columns you'll use most

#### Day 2: Database Creation & Data Loading
**Morning:**
- Create the database using the schema above
- Write `create_database.py`:
  ```python
  import sqlite3

  # Read and execute schema
  with open('schema.sql', 'r') as f:
      schema = f.read()

  conn = sqlite3.connect('db/airbnb.db')
  conn.executescript(schema)
  conn.close()
  print("Database created successfully!")
  ```

**Afternoon:**
- Write `load_data.py` to load CSVs into SQLite:
  ```python
  import pandas as pd
  import sqlite3
  import json

  # Connect to database
  conn = sqlite3.connect('db/airbnb.db')

  # Load listings
  print("Loading listings...")
  listings = pd.read_csv('data/raw/listings.csv.gz', compression='gzip')

  # Clean and transform
  listings['price_numeric'] = listings['price'].str.replace('$', '').str.replace(',', '').astype(float)
  listings['host_is_superhost'] = listings['host_is_superhost'].map({'t': 1, 'f': 0})
  listings['instant_bookable'] = listings['instant_bookable'].map({'t': 1, 'f': 0})
  listings['host_identity_verified'] = listings['host_identity_verified'].map({'t': 1, 'f': 0})

  # Select columns that match our schema
  # (Map CSV column names to our database column names)
  listings.to_sql('listings', conn, if_exists='append', index=False)

  # Load calendar
  print("Loading calendar...")
  # Load in chunks (it's big!)
  for chunk in pd.read_csv('data/raw/calendar.csv.gz', compression='gzip', chunksize=100000):
      chunk['available'] = chunk['available'].map({'t': 1, 'f': 0})
      chunk['price_numeric'] = chunk['price'].str.replace('$', '').str.replace(',', '').astype(float)
      chunk.to_sql('calendar', conn, if_exists='append', index=False)

  # Load reviews
  print("Loading reviews...")
  reviews = pd.read_csv('data/raw/reviews.csv.gz', compression='gzip')
  reviews.to_sql('reviews', conn, if_exists='append', index=False)

  conn.close()
  print("All data loaded!")
  ```

**Troubleshooting:** If loading fails, check:
- Column names in CSV match your expectations
- Price parsing doesn't have edge cases
- Memory isn't exhausted (use chunksize for large files)

#### Day 3: Data Audit (Tier 0)
**Full day:** Complete Tier 0 deliverables in `notebooks/02_tier0_audit.ipynb`

**Starter queries:**
```sql
-- How many listings per borough?
SELECT neighbourhood_group_cleansed, COUNT(*) as count
FROM listings
GROUP BY neighbourhood_group_cleansed
ORDER BY count DESC;

-- Room type distribution
SELECT room_type, COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 1) as pct
FROM listings
GROUP BY room_type
ORDER BY count DESC;

-- Date range of reviews
SELECT MIN(date) as earliest, MAX(date) as latest,
       COUNT(DISTINCT listing_id) as listings_with_reviews
FROM reviews;

-- Listings with zero reviews
SELECT COUNT(*) as zero_review_count,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 1) as pct
FROM listings
WHERE number_of_reviews = 0;

-- Price range by borough
SELECT neighbourhood_group_cleansed as borough,
       ROUND(MIN(price_numeric), 2) as min_price,
       ROUND(AVG(price_numeric), 2) as avg_price,
       ROUND(MAX(price_numeric), 2) as max_price
FROM listings
WHERE price_numeric > 0
GROUP BY neighbourhood_group_cleansed;
```

#### Day 4: Tier 0 Review & Documentation
- Review your findings with your team
- Document data quality issues (missing values, outliers, etc.)
- Fix any data loading issues
- **Checkpoint:** Can you explain what's in the dataset to someone who hasn't seen it?

#### Days 5-7: Buffer / Catch-up
- Finish any incomplete Tier 0 work
- Start exploring Tier 1 questions
- Read ahead on SQL aggregation functions

---

### Week 2: Market Overview — Tier 1 (Days 8-14)
**Goal:** Answer "Can we compete?" with data and charts

#### Day 8: Revenue Analysis
**Learn:** How to use the pre-calculated revenue estimates

```sql
-- Revenue by neighborhood (using pre-calculated field)
SELECT
    neighbourhood_cleansed as neighbourhood,
    COUNT(*) as listings,
    ROUND(AVG(estimated_revenue_l365d), 0) as avg_revenue,
    ROUND(AVG(estimated_occupancy_l365d), 0) as avg_occupancy
FROM listings
WHERE estimated_revenue_l365d > 0
GROUP BY neighbourhood_cleansed
ORDER BY avg_revenue DESC
LIMIT 20;
```

#### Day 9: Borough Comparison Charts
**Learn:** matplotlib bar charts

```python
import matplotlib.pyplot as plt
import pandas as pd

# Query data
borough_stats = pd.read_sql("""
    SELECT
        neighbourhood_group_cleansed as borough,
        COUNT(*) as listings,
        ROUND(AVG(price_numeric), 2) as avg_price
    FROM listings
    WHERE price_numeric > 0 AND price_numeric < 1000
    GROUP BY neighbourhood_group_cleansed
    ORDER BY listings DESC
""", conn)

# Create bar chart
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].bar(borough_stats['borough'], borough_stats['listings'])
axes[0].set_title('Number of Listings by Borough')
axes[0].set_ylabel('Count')

axes[1].bar(borough_stats['borough'], borough_stats['avg_price'])
axes[1].set_title('Average Price by Borough')
axes[1].set_ylabel('Price ($)')

plt.tight_layout()
plt.savefig('output/charts/borough_comparison.png')
plt.show()
```

#### Days 10-11: Room Type Analysis
- Create pie chart of room type distribution
- Calculate and visualize price by room type
- Analyze occupancy by room type

#### Days 12-13: Neighborhood Deep Dive
- Top 10 neighborhoods by revenue
- Revenue distribution histograms
- Compare neighborhoods within each borough

#### Day 14: Tier 1 Presentation
- Compile all charts into a presentation
- Write 1-2 sentence summary for each finding
- **Checkpoint:** Present your Tier 1 findings to your partner team

---

### Week 3: Location Scoring — Tier 2 (Days 15-21)
**Goal:** Build a scoring system to rank neighborhoods

#### Days 15-16: Ghost Listing Analysis
```sql
-- Ghost listings: no reviews in 12 months AND high availability
SELECT
    neighbourhood_cleansed,
    COUNT(*) as total_listings,
    SUM(CASE
        WHEN number_of_reviews_ltm = 0 AND availability_365 > 300
        THEN 1 ELSE 0
    END) as ghost_listings,
    ROUND(100.0 * SUM(CASE
        WHEN number_of_reviews_ltm = 0 AND availability_365 > 300
        THEN 1 ELSE 0
    END) / COUNT(*), 1) as ghost_rate
FROM listings
GROUP BY neighbourhood_cleansed
ORDER BY ghost_rate DESC;
```

#### Days 17-18: Host Concentration
```sql
-- Top hosts by number of listings
SELECT
    host_id,
    host_name,
    COUNT(*) as num_listings,
    GROUP_CONCAT(DISTINCT neighbourhood_group_cleansed) as boroughs
FROM listings
GROUP BY host_id
ORDER BY num_listings DESC
LIMIT 20;

-- Market concentration by borough
SELECT
    neighbourhood_group_cleansed as borough,
    COUNT(DISTINCT host_id) as unique_hosts,
    COUNT(*) as total_listings,
    ROUND(1.0 * COUNT(*) / COUNT(DISTINCT host_id), 1) as listings_per_host
FROM listings
GROUP BY neighbourhood_group_cleansed;
```

#### Days 19-20: Seasonal Patterns
```sql
-- Monthly occupancy from calendar
SELECT
    strftime('%m', date) as month,
    ROUND(100.0 * SUM(CASE WHEN available = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as occupancy_rate,
    ROUND(AVG(price_numeric), 2) as avg_price
FROM calendar
WHERE price_numeric > 0
GROUP BY month
ORDER BY month;
```

#### Day 21: Composite Score & Tier 2 Presentation
Build your scoring formula and present top neighborhoods.

---

### Week 4: Deep Analysis — Tier 3 (Days 22-28)
**Goal:** Build models and dashboard

#### Days 22-23: Price Prediction Model
```python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Prepare features
features = pd.read_sql("""
    SELECT
        price_numeric,
        accommodates,
        bedrooms,
        review_scores_rating,
        number_of_reviews,
        availability_365,
        CASE WHEN room_type = 'Entire home/apt' THEN 1 ELSE 0 END as is_entire_home,
        CASE WHEN room_type = 'Private room' THEN 1 ELSE 0 END as is_private_room
    FROM listings
    WHERE price_numeric > 0 AND price_numeric < 1000
      AND review_scores_rating IS NOT NULL
""", conn)

X = features.drop('price_numeric', axis=1)
y = features['price_numeric']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
print(f"R² Score: {r2_score(y_test, predictions):.3f}")
print(f"MAE: ${mean_absolute_error(y_test, predictions):.2f}")

# Feature importance
importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(importance)
```

#### Days 24-25: Amenity Analysis
- Parse amenities JSON
- Calculate price premium per amenity
- Visualize top amenities

#### Days 26-27: Dashboard Development
**Option A: Streamlit (recommended for beginners)**
```bash
pip install streamlit
```

```python
# app.py
import streamlit as st
import pandas as pd
import sqlite3

st.title("NYC Hostel Location Analyzer")

conn = sqlite3.connect('db/airbnb.db')

# Sidebar filters
borough = st.sidebar.selectbox("Select Borough", [
    "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"
])

# Main content
data = pd.read_sql(f"""
    SELECT * FROM neighbourhood_summary
    WHERE borough = '{borough}'
    ORDER BY avg_price DESC
""", conn)

st.dataframe(data)
```

**Option B: Jupyter Widgets (no extra install)**
- Use `ipywidgets` for interactive filters
- Embed charts directly in notebook

#### Day 28: Tier 3 Presentation
- Demo your dashboard
- Present model results
- Show feature importance analysis

---

### Weeks 5-6: Dashboard Polish & Integration
- Connect all tiers into one cohesive dashboard
- Add map visualizations
- User testing and feedback

### Week 7: Report Writing
- Document methodology
- Compile findings
- Create executive summary

### Week 8: Presentation Prep
- Slide deck creation
- Demo rehearsal
- Q&A preparation

---

## 🧰 Starter Code: What I'll Provide

I will create these files for you:

### 1. `schema.sql` ✅ (Above)
Complete database schema with tables, indexes, and views.

### 2. `scripts/create_database.py` ✅
Script to create the SQLite database from the schema.

### 3. `scripts/load_data.py` ✅
Script to load all CSVs into the database with proper cleaning.

### 4. `scripts/validate_data.py` ✅
Script to run validation checks and print data quality report.

### 5. `notebooks/02_tier0_starter.ipynb` ✅
Interactive notebook for Tier 0 with sample queries and visualizations.

### 6. `data_dictionary.md` ✅
Document explaining every field in the database.

### 7. `requirements.txt` ✅
List of all Python packages needed.

### 8. `README.md` ✅
Project overview and getting started guide.

### 9. `schema.sql` ✅
Complete database schema with tables, indexes, and views.

---

## ✅ Validation Checkpoints

After each tier, verify your work:

### Tier 0 Checkpoint
- [ ] Database created with correct schema
- [ ] All 3 CSVs loaded (listings: 50,281 rows, calendar: ~2.4M rows, reviews: ~1.3M rows)
- [ ] No duplicate listing IDs
- [ ] All prices parseable as numbers
- [ ] Summary statistics printed and documented
- [ ] Data quality issues identified and documented

### Tier 1 Checkpoint
- [ ] Average price calculated by borough
- [ ] Room type distribution visualized
- [ ] Revenue estimates calculated
- [ ] At least 6 charts created
- [ ] Can explain: "In [borough], the average nightly rate is $X, with Y% occupancy, generating $Z estimated annual revenue."

### Tier 2 Checkpoint
- [ ] Ghost listings identified and quantified
- [ ] Host concentration analyzed
- [ ] Seasonal patterns visualized
- [ ] Composite scoring formula defined
- [ ] Top 5 neighborhoods ranked with explanations
- [ ] At least one "hidden gem" identified

### Tier 3 Checkpoint
- [ ] Price prediction model built and evaluated
- [ ] Feature importance analyzed
- [ ] Amenity impact calculated
- [ ] Dashboard created and functional
- [ ] All tiers integrated into cohesive analysis

---

## 📊 Final Deliverable Format

Your final submission should include:

### 1. Technical Report (PDF or Markdown)
**Structure:**
1. Executive Summary (1 page)
2. Methodology (1-2 pages)
3. Data Overview (1 page)
4. Findings by Tier (3-5 pages)
5. Recommendations (1 page)
6. Appendix (queries, code, additional charts)

### 2. Interactive Dashboard
- Streamlit app OR
- Jupyter notebook with widgets
- Must include: map, filters, comparison charts

### 3. Code Repository
- Well-organized folder structure
- README with setup instructions
- Comments explaining complex logic
- requirements.txt for dependencies

### 4. Presentation (10-15 minutes)
- Problem statement
- Data overview
- Key findings (1-2 per tier)
- Recommendation
- Live demo of dashboard

---

## 💡 Tips for Success

### For Complete Beginners

1. **Start small.** Don't try to build everything at once. Complete Tier 0 first, then move on.

2. **Copy and modify.** The starter code is there to help you. Don't feel like you need to write everything from scratch.

3. **Google is your friend.** Every error you encounter has been encountered by someone else. Search for the error message.

4. **Ask for help early.** If you're stuck for more than 30 minutes, ask your mentor or teammate.

5. **Test your queries.** Before writing complex SQL, test with a small `LIMIT 10` to make sure you're getting what you expect.

6. **Save your work.** Commit to Git frequently. Use meaningful commit messages.

7. **Document as you go.** Write comments in your code. Create a log of what you've learned.

### Common Pitfalls to Avoid

1. **Don't skip Tier 0.** You need to understand the data before you can analyze it.

2. **Don't ignore data quality.** Missing values and outliers will skew your analysis. Handle them explicitly.

3. **Don't over-engineer.** A simple solution that works is better than a complex solution that's broken.

4. **Don't work in isolation.** Pair program, review each other's code, and discuss findings.

5. **Don't forget the "why."** Always connect your analysis back to the business question: "Where should we open a hostel?"

### When You're Stuck

1. Check the error message carefully
2. Google the error message
3. Check if your data looks like you expect
4. Ask a teammate
5. Ask your mentor
6. Take a break and come back fresh

---

## 🎓 What You'll Learn

By completing this project, you will:

1. **SQL:** Write complex queries with JOINs, aggregations, and subqueries
2. **Python:** Use pandas for data manipulation and matplotlib/seaborn for visualization
3. **Data Analysis:** Clean, transform, and analyze real-world data
4. **Statistics:** Understand distributions, correlations, and basic modeling
5. **Machine Learning:** Build and evaluate a prediction model
6. **Data Visualization:** Create effective charts and dashboards
7. **Communication:** Present technical findings to non-technical audiences
8. **Project Management:** Work in a team, manage deadlines, deliver results

---

## 📅 Quick Reference Calendar

| Week | Days | Focus | Tier | Key Deliverable |
|------|------|-------|------|-----------------|
| 1 | 1-7 | Setup + Data Audit | 0 | Database + Data Quality Report |
| 2 | 8-14 | Market Overview | 1 | Borough Comparison Charts |
| 3 | 15-21 | Location Scoring | 2 | Neighborhood Scorecard |
| 4 | 22-28 | Deep Analysis | 3 | Price Model + Dashboard |
| 5-6 | 29-42 | Dashboard Polish | — | Final Dashboard |
| 7 | 43-49 | Report Writing | — | Technical Report |
| 8 | 50-56 | Presentation Prep | — | Final Presentation |

---

*This brief was designed to take you from zero to data analyst in 8 weeks. Follow the steps, use the starter code, and don't be afraid to ask questions. You've got this!*
