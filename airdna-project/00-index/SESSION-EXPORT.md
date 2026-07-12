# Session Export — AirDNA Clone Project

> **Date:** 2026-06-28
> **Duration:** ~6 hours of research and API cracking
> **Status:** Research 95% complete, API cracked for Airbnb + Booking.com

---

## What Was Accomplished

### 1. AirDNA Deep Research (7 rounds)
- 49 sections of research on AirDNA's product, tech stack, algorithms, pricing
- Confirmed tech stack: Scala + Spark + Kafka + Airflow + Druid + Flask + S3 + MLflow + XGBoost
- Revenue: $44.5M, 160 employees, acquired by Alpine Investors (PE) March 2022
- No patents — moat is data accumulation + ML refinement
- All 5 sub-models documented (Matching, Reservation, Pricing, Revenue Potential, Analyzation)

### 2. Airbnb Shadow API — CRACKED
- **API Key:** `d306zoyjsyarp7ifhu67rjxn52tv0t20` (public, embedded in frontend)
- **14 GraphQL operations** discovered with SHA256 hashes
- **StaysPdpSections** — listing detail, pricing, availability, house rules (60KB response)
- **PdpAvailabilityCalendar** — calendar data (works with cookies)
- **StaysSearch** — SSR blob with 423KB of search results
- Working curl examples and Python code

### 3. Airbnb Search — CRACKED
- SSR blob approach: `<script id="data-deferred-state-0">` contains 380KB+ JSON
- 18 listings per page, pagination in steps of 18
- Listing IDs: `DemandStayListing:{numeric_id}` (base64 encoded)
- All filter parameters documented (dates, guests, price, amenities, etc.)

### 4. Airbnb Calendar — CRACKED
- `PdpAvailabilityCalendar` works with session cookies
- Returns 3 months of daily availability
- Each day: available, bookable, minNights, maxNights, checkin/checkout flags
- Cookie extraction via Playwright works

### 5. Booking.com GraphQL — CRACKED
- Endpoint: `https://www.booking.com/dml/graphql`
- Property cards with: ID, name, type, rating, reviews, price, city, country
- 16 GraphQL responses captured (largest: 155KB)

### 6. Vrbo — ATTEMPTED (blocked)
- Playwright automation captured 0 responses
- Anti-bot protection detected
- Need residential proxies for Vrbo

### 7. Complete Blueprint
- Booking detection algorithm (calendar diff + 4 heuristics)
- Cross-platform matching (XGBoost, 14 features, 95% recall)
- Revenue estimation (Rentalizer clone)
- Dynamic pricing (6 modifiers)
- Market aggregation
- Anomaly detection
- Comp set algorithm
- Filter system
- Legal considerations
- MVP scope & differentiation
- API design & revenue model

---

## Remaining Work

| Priority | Task | Status |
|---|---|---|
| 🔴 | Vrbo scraping (needs proxies) | Blocked |
| 🔴 | Seasonality decomposition implementation | Not started |
| 🔴 | Event/holiday detection API | Not started |
| 🔴 | STR regulation data source | Not started |
| 🔴 | Data pipeline implementation (ETL) | Not started |
| 🔴 | ML model training (XGBoost) | Not started |
| 🟡 | Booking.com search results endpoint | Partial |
| 🟡 | Rate limiting testing | Not started |
| 🟡 | Error handling patterns | Not started |
| 🟢 | Customer validation | Not started |
| 🟢 | Competitor deep dives | Not started |

---

## Key Algorithms

### Booking Detection
```
Calendar diff → available→unavailable = potential booking
Score = LOS(0.35) + window(0.30) + market(0.20) + price(0.15)
Score > 0.6 = real booking
```

### Matching (XGBoost)
```
14 features: location, title, description, bedrooms, calendar...
Recall: 95%, Frequency: monthly
```

### Rentalizer
```
Inputs: lat, lng, beds, baths, guests (5 only)
Process: find comps 10mi → weight by similarity → trailing 12mo
Output: revenue + confidence intervals
```

### Smart Rates
```
Daily Rate = Base × (1 + demand + event + lead_time + orphan + seasonality + dow)
```

### Comp Score
```
Score = 100 - distance/50 - bed_mismatch(15) - bath_mismatch(10) - guest_mismatch(10) - type_mismatch(10) - listing_mismatch(15) - rating_diff×5
```

---

## Build Order

| Phase | What | Time |
|---|---|---|
| **Week 1** | Calendar scraper + booking inference | 5 days |
| **Week 2** | Listing data pipeline + cleaning | 5 days |
| **Week 3** | Market aggregation + metrics | 5 days |
| **Week 4** | Revenue estimator | 5 days |
| **Week 5-6** | Cross-platform matching | 10 days |
| **Week 7-8** | Dynamic pricing | 10 days |
| **Week 9-10** | Frontend dashboard | 10 days |
