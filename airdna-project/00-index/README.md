# AirDNA Clone Project — Master Index

> **Goal:** Build an AirDNA competitor from scratch
> **Started:** 2026-06-28
> **Status:** Research complete (7 rounds + wide research), API cracked, blueprint ready

---

## 📁 Project Structure (41 files, 324KB)

```
airdna-project/
├── 00-index/
│   └── README.md                    ← You are here
├── 01-airdna-research/ (13 files)   ← AirDNA company, tech, algorithms, pricing, API
├── 02-airbnb-api/ (7 files)         ← Cracked API, GraphQL, search, cookies, Vrbo/Booking
├── 03-tools-and-methods/ (4 files)  ← Scraping, HAR, anti-bot, reverse engineering
├── 04-clone-blueprint/ (14 files)   ← All components + legal + MVP + revenue model
└── 05-data-samples/ (2 files)       ← Real API responses
```

---

## 🎯 What We Know

### AirDNA
- Scrapes Airbnb, Vrbo, Booking.com daily (16M+ listings, 120K markets)
- 5 sub-models: Matching (XGBoost, 14 features, 95% recall), Reservation, Pricing, Revenue Potential, Analyzation
- Tech stack: Scala + Spark + Kafka + Airflow + Druid + Flask + S3 + MLflow + XGBoost
- Infrastructure: AWS (Kubernetes, ELB), Cloudflare CDN
- Revenue: $44.5M, 160 employees, acquired by Alpine Investors (PE) March 2022
- No patents — moat is data accumulation + ML refinement

### What We Cracked
- Airbnb GraphQL API — public key, 14 operations, direct curl
- StaysPdpSections — listing detail, pricing, availability (60KB)
- PdpAvailabilityCalendar — calendar data (needs cookies)
- StaysSearch — SSR blob with 380KB of search results
- Booking.com GraphQL — internal API at `/api/graphql`
- PriceLabs booking detection — calendar diff + 4 heuristics
- Rentalizer formula — distance + similarity weighted average
- Smart Rates — 6 modifier types, base rate calculation
- XGBoost matching — 14 features, 95% recall
- Full infrastructure mapping — Spark, Kafka, Druid, Airflow, S3, K8s

---

## 🔑 Key Credentials

| Item | Value |
|---|---|
| Airbnb API Key | `d306zoyjsyarp7ifhu67rjxn52tv0t20` |
| Airbnb GraphQL | `https://www.airbnb.com/api/v3/{Op}/{Hash}` |
| AirDNA API | `https://api.airdna.co/api/enterprise/v2/` |
| Booking.com GraphQL | `https://www.booking.com/api/graphql` |

---

## 📊 Key Algorithms

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

## 📅 Build Order

| Phase | What | Time |
|---|---|---|
| **Week 1** | Calendar scraper + booking inference | 5 days |
| **Week 2** | Listing data pipeline + cleaning | 5 days |
| **Week 3** | Market aggregation + metrics | 5 days |
| **Week 4** | Revenue estimator | 5 days |
| **Week 5-6** | Cross-platform matching | 10 days |
| **Week 7-8** | Dynamic pricing | 10 days |
| **Week 9-10** | Frontend dashboard | 10 days |

---

## 📚 Key References

- PriceLabs methodology: hello.pricelabs.co/blog/science-behind-pricelabs-data/
- HBS case study: "AirDNA: Smarter Short Term Rental Pricing"
- Airbnb Aerosolve: github.com/airbnb/aerosolve
- InsideAirbnb: insideairbnb.com/get-the-data/
- Guestready client: github.com/guestready/airdna-api
- browse.sh Airbnb skill: browse.sh/skills/airbnb.com/search-listings-ddgioa.md
- Booking.com GraphQL: verified via HAR capture (see 02-airbnb-api/booking-graphql-cracked.md)
