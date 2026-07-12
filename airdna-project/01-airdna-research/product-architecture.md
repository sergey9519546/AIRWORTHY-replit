# AirDNA Product Architecture

> How AirDNA works, what it does, what it charges

---

## What AirDNA Is
- Short-term rental analytics platform
- Tracks 10M+ listings across 120K markets globally
- Scrapes Airbnb, Vrbo, Booking.com daily
- Founded 2015, trusted by 1.3M+ users
- Banks use it for underwriting, hedge funds for investment decisions

## Pricing (2026)

| Plan | Price | What You Get |
|---|---|---|
| Explorer (Free) | $0/mo | Basic market overview, top-level stats |
| Starter | ~$15/mo | Individual property lookup, revenue estimates |
| Professional | ~$25-40/mo | Full analytics, historical data, exports |
| Enterprise | Custom | API access, bulk data, team accounts |

> Source: Awning review, April 2026

## The 5 Sub-Models (Data Model 5.0)

### 1. Analyzation Model
- Decides most accurate metrics daily
- Handles conflicting data from multiple scrapes

### 2. Matching Model
- Cross-platform deduplication
- Same property on Airbnb + Vrbo + Booking.com
- Uses address, coordinates, photos, metadata

### 3. Reservation Model (THE SECRET)
- Distinguishes real bookings from host-blocked days
- Calendar-based inference
- Nobody outside AirDNA knows exact algorithm
- **We reverse-engineered PriceLabs' version**

### 4. Pricing Model
- Updated in 2023 for Airbnb's date-gated pricing
- Now requires date-by-date scraping

### 5. Anomaly Detection
- Filters outlier data
- Removes fake/inactive listings
- Quality scoring

## Revenue Streams
1. **Subscription fees** (main revenue)
2. **Enterprise API** (sales-gated, expensive)
3. **Rentalizer lead gen** (embedded on partner sites)
4. **Smart Rates** (dynamic pricing for hosts)

## Competitors

| Company | Differentiator |
|---|---|
| **PriceLabs** | Dynamic pricing focus, open methodology |
| **Airbtics** | Cheaper, 98% accuracy claim |
| **InsideBnb** | ZIP-level granularity, $5.99/market |
| **Mashvisor** | Traditional rental + STR |
| **Rabbu** | Free calculator, comp-based |
| **InsideAirbnb** | Free, open-source, academic-grade |

## Tech Stack (from recon)
- **Frontend:** React SPA (Vite-bundled)
- **Auth:** OAuth2 at auth.airdna.co (Google Sign-In)
- **API:** REST at api.airdna.co/api/enterprise/v2/
- **Analytics:** Segment → GA, Facebook, Hotjar, Amplitude, HubSpot
- **Maps:** Mapbox
- **Subscription:** ProfitWell
- **Referral:** Ambassador API
