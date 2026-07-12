# All 5 Sub-Models — Fully Documented

> From HBS AI Institute case study + AirDNA source code

---

## Model 5.0 (2025) — The 5 Sub-Models

| # | Sub-Model | Description |
|---|---|---|
| 1 | **Matching** | Removes duplicate data across platforms |
| 2 | **Reservation** | Detects true bookings vs. blocked days |
| 3 | **Pricing** | Generates daily prices for every listing |
| 4 | **Revenue Potential** | Estimates what any property could earn |
| 5 | **Analyzation** | Decides the most accurate metrics daily |

---

## Algorithm 1: Reservation Algorithm

**Purpose:** Distinguish blocked vs. reserved days to paint accurate demand picture

**Method (from HBS):**
- Analyzes historical occupancy rates and booking lead times of every STR
- Predicts travel demand up to 6 months into the future based on real-time future bookings
- Creates **booking curve** based on average occupancy rates and how far in advance properties were booked in previous 12 months
- Analyzes real-time booking fluctuations from standard booking curve to identify periods of high/low demand
- **Demand Score** computed from deviation from standard booking curve

**Filters:** Market, rental type, beds, accommodates

**Our reverse-engineered version (PriceLabs method):**
- Calendar diff → available→unavailable = potential booking
- 4 heuristics: length of stay (0.35), booking window (0.30), market correlation (0.20), price variation (0.15)
- Score > 0.6 = likely booking

---

## Algorithm 2: Matching Algorithm

**Purpose:** Identify properties listed on multiple platforms

**Algorithm:** XGBoost Classifier (Python) — CONFIRMED from HBS AI Institute

**Features:** 14+ listing features:
1. Location (lat/lng)
2. Listing titles
3. Listing descriptions
4. Number of bedrooms
5. Calendar availability
6. (9+ additional features not disclosed)

**Performance:**
- **Recall score:** 95%
- **Scale:** Analyzes over 10M listings globally
- **Frequency:** Recalculates matches monthly
- **Challenge:** Properties cannot be identified by physical address (intentionally obfuscated by OTAs)
- **Overlap:** Varies widely — some markets have up to 45% Airbnb/Vrbo overlap, others have almost none

**Our implementation approach:**
- Geographic proximity (GPS within 50m)
- Property type match
- Bed/bath/guest capacity match
- Photo perceptual hashing (imagehash)
- Title/description fuzzy matching (rapidfuzz)
- Threshold >0.65 = same property

---

## Algorithm 3: Pricing Algorithm (Smart Rates)

**Purpose:** Provide recommended daily rates for specific properties

**Inputs:**
1. Booking demand (number of rentals booked, pick-up rate, % booked)
2. Seasonality
3. Base rate
4. Market influences
5. Performance data
6. Booking lead time

**Output:** Daily recommended rates with attribution breakdown

**Three strategies:**
1. **High ADR** — Maximize average daily rate
2. **High Occupancy** — Maximize occupancy
3. **Balanced** — Optimize balance between ADR and Occupancy

**Base Rate Requirements:**
- At least 5 reserved days with valid price in last year
- At least 5 comps with 15+ days reserved in last year
- City must have 50+ reserved nights in last year

**Daily Rate = Base Rate × (1 + sum of modifiers)**

**Modifier types:**
1. **Demand Score** — Real-time demand signal (-1.0 to +1.0)
2. **Holiday/Event** — Premium for holidays and local events
3. **Lead Time** — How far in advance the booking is
4. **Orphan** — Discount for isolated single nights between bookings
5. **Seasonality** — Monthly/seasonal patterns
6. **Day of Week** — Weekday vs weekend pricing

**Orphan day modifiers:** Built-in support for 1-day and 2-day orphan gap pricing

---

## Algorithm 4: Revenue Potential (Rentalizer)

**Purpose:** Estimate revenue for any property

**Inputs (exactly 5):**
- `accommodates` (integer)
- `bathrooms` (integer)
- `bedrooms` (integer)
- `lat` (string)
- `lng` (string)

**Process:**
1. Takes lat/lng + property specs
2. Queries all active listings within geographic radius (10 miles)
3. Filters comps by bedroom count, bathroom count, accommodates
4. Pulls trailing 12-month performance data for comp set
5. Applies ML model to weight comps by recency, similarity, performance
6. Calculates monthly ADR, occupancy, revenue projections
7. Generates confidence intervals (revenue_lower / revenue_upper)
8. Estimates property value (likely comparable sales + income approach)

**Key insight:** Only 5 inputs. No amenity data, no property type, no review count, no photos. The model infers everything from geographic comps.

---

## Algorithm 5: Analyzation

**Purpose:** Decides the most accurate metrics daily

**Function:**
- Handles conflicting data from multiple scrapes per day
- Selects best representation of each metric
- Quality control layer from partner data (100K+ properties with real reservation data)
- Continuously validates and fine-tunes analyzed data

---

## Evolution Timeline
- **2015 — Model 1.0:** Industry's first STR reservation model
- **2018 — Model 2.0:** Introduced Vrbo and cross-platform matching
- **2019 — Model 3.0:** Rebuilt for major Airbnb API changes
- **2023 — Model 4.0:** Updated for Airbnb's date-selection pricing change
- **2025 — Model 5.0:** Five sub-models, 2x accuracy for mid/long-term stays, stronger anomaly detection

## Accuracy Claims
- **Self-reported:** "95%+ accurate to Airbnb's public reporting"
- **Scope:** Market-level aggregate revenue (NOT individual listings)
- **Validation:** Compares against Airbnb's occasional public disclosures
- **No independent audit** published
- **Rentalizer accuracy:** Not separately disclosed

## Key Data Points
- **Total listings:** 16M+ daily (up from 10M+ previously stated)
- **Partner data:** 100K+ properties with real reservation data
- **Direct data sources:** Property managers and hosts share real data
- **Legal status:** Can legally scrape (per HBS case study)
- **Risk:** Future regulation could limit scraping ability
