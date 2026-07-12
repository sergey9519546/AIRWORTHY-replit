# Dataset Sources — Complete Guide

> Every data source your AirDNA clone needs, organized by category

---

## 1. STR LISTING DATA (Core)

### Free / Open Source

| Source | Data | Coverage | Format | URL |
|---|---|---|---|---|
| **Inside Airbnb** | Listings, calendar, reviews, neighbourhoods | 100+ cities, quarterly | CSV/GeoJSON | insideairbnb.com/get-the-data/ |
| **Tom Slee** | Historical Airbnb data (2013-2017) | 100+ cities | CSV (S3) | tomslee.net/airbnb-data-collection-get-the-data |
| **Kaggle Airbnb Open Data** | Listings, reviews | Multiple cities | CSV | kaggle.com/datasets/arianazmoudeh/airbnbopendata |

### Paid / API

| Source | Data | Coverage | Pricing | URL |
|---|---|---|---|---|
| **AirDNA** | Listings, metrics, revenue, comps | 16M+ listings, 120K markets | $20-120/mo + API | airdna.co |
| **AirROI** | Listings, analytics, revenue | 20M+ properties, 190+ countries | API pricing | airroi.com |
| **Airbtics** | Listings, occupancy, revenue | Global | Paid plans | airbtics.com |
| **Mashvisor** | Listings, analytics | US-focused | Paid plans | mashvisor.com |
| **PriceLabs** | Market dashboards, pricing | Global | Paid plans | pricelabs.co |
| **Rabbu** | Revenue estimates | US-focused | Free calculator + paid | rabbu.com |
| **Awning** | Revenue estimates | US-focused | Free calculator | awning.com/airbnb-calculator |

### We Have (Cracked)

| Platform | Method | Status |
|---|---|---|
| **Airbnb** | GraphQL shadow API + SSR blob | ✅ Working |
| **Booking.com** | GraphQL at /dml/graphql | ✅ Working |
| **Vrbo** | Browser automation | ❌ Blocked (needs proxies) |

---

## 2. CALENDAR / AVAILABILITY DATA

| Source | Data | Method | Status |
|---|---|---|---|
| **Airbnb GraphQL** | Daily availability, min/max nights | PdpAvailabilityCalendar + cookies | ✅ Working |
| **Inside Airbnb** | Calendar snapshots (quarterly) | CSV download | ✅ Free |
| **Airbnb SSR blob** | Embedded in search results | Parse <script> tag | ✅ Working |

---

## 3. EVENTS & HOLIDAYS

### Public Holidays (Free)

| Source | Coverage | Format | URL |
|---|---|---|---|
| **Nager.Date** | 100+ countries, no rate limits | JSON API | date.nager.at/api |
| **OpenHolidays API** | Worldwide | JSON API | openholidaysapi.org |
| **API Ninjas Holidays** | Worldwide | JSON API | api-ninjas.com/api/holidays |
| **Google Calendar** | Public holidays | ICS/JSON | google.com/calendar |

**Nager.Date Example:**
```
GET https://date.nager.at/api/v3/PublicHolidays/2026/US
```
Returns: date, localName, name, countryCode, global, types

### Events (Concerts, Sports, Conferences)

| Source | Data | Coverage | Pricing | URL |
|---|---|---|---|---|
| **PredictHQ** | Concerts, sports, conferences, festivals | Global | Paid (expensive) | predicthq.com |
| **Ticketmaster** | Concerts, sports events | US + international | Free tier (5K calls/day) | developer.ticketmaster.com |
| **Eventbrite** | Conferences, meetups, events | Global | Free tier | eventbrite.com/platform |
| **SeatGeek** | Sports, concerts | US | Free tier | platform.seatgeek.com |
| **ESPN API** | Sports schedules | US | Free | api.espn.com |
| **TheSportsDB** | Sports events, schedules | Global | Free/Paid | thesportsdb.com |
| **Songkick** | Concerts | Global | Free API | songkick.com/developer |

**Best Free Option:** Ticketmaster Discovery API (5K free calls/day)

---

## 4. GEOGRAPHIC / LOCATION DATA

### Geocoding (Free)

| Source | Coverage | Rate Limit | URL |
|---|---|---|---|
| **Nominatim (OpenStreetMap)** | Worldwide | 1 req/sec | nominatim.openstreetmap.org |
| **Google Geocoding** | Worldwide | $5/1000 requests | developers.google.com/maps |
| **Mapbox Geocoding** | Worldwide | 100K free/mo | mapbox.com |
| **Geoapify** | Worldwide | 3K free/day | geoapify.com |
| **Pelias (open source)** | Worldwide | Self-hosted free | pelias.io |

### Boundaries / Neighborhoods

| Source | Data | Format | URL |
|---|---|---|---|
| **OpenStreetMap** | Neighborhoods, boundaries | GeoJSON | openstreetmap.org |
| **Inside Airbnb** | Neighbourhood GeoJSON per city | GeoJSON | insideairbnb.com/get-the-data/ |
| **US Census TIGER** | US boundaries, zip codes | Shapefile | census.gov |
| **Natural Earth** | Country, state, city boundaries | Shapefile/GeoJSON | naturalearthdata.com |
| **Who's on First** | Neighborhoods worldwide | GeoJSON | whosonfirst.org |

---

## 5. REAL ESTATE / PROPERTY VALUES

| Source | Data | Coverage | Pricing | URL |
|---|---|---|---|---|
| **Zillow API** | Property values, Zestimates | US | Free tier | zillow.com/webservice |
| **Redfin** | Sales data, estimates | US | Scraping | redfin.com |
| **ATTOM Data** | Tax, deed, valuation (158M properties) | US | $95+/mo | attomdata.com |
| **RentCast** | Rental estimates, property data | US | Free tier | rentcast.io |
| **CoreLogic** | Property data | US | Enterprise | corelogic.com |
| **HouseCanary** | Property valuations | US | Enterprise | housecanary.com |
| **BatchData** | Property data, owner info | US | API pricing | batchdata.io |

**Best Free Option:** Zillow API (basic property data) + RentCast (rental estimates)

---

## 6. DEMOGRAPHICS & ECONOMICS

| Source | Data | Coverage | Format | URL |
|---|---|---|---|---|
| **US Census Bureau** | Population, income, housing | US | API/CSV | census.gov/data |
| **World Bank** | GDP, population, tourism | Global | API/CSV | data.worldbank.org |
| **UN Tourism** | Tourist arrivals, receipts | Global | CSV | untourism.int/tourism-statistics |
| **Our World in Data** | Tourism, demographics | Global | CSV | ourworldindata.org |
| **Bureau of Labor Statistics** | Employment, wages | US | API | bls.gov |
| **FRED (Federal Reserve)** | Economic indicators | US | API | fred.stlouisfed.org |

---

## 7. TOURISM DATA

| Source | Data | Coverage | Format | URL |
|---|---|---|---|---|
| **UN Tourism Dashboard** | International arrivals, receipts | Global | CSV | untourism.int/tourism-data |
| **US Travel Association** | Domestic travel stats | US | Reports | ustravel.org |
| **STR (Smith Travel)** | Hotel occupancy, ADR, RevPAR | Global | Paid | str.com |
| **Tourism Economics** | Tourism impact data | Global | Paid | tourismeconomics.com |
| **Google Trends** | Search demand signals | Global | API | trends.google.com |

---

## 8. WEATHER DATA

| Source | Data | Coverage | Pricing | URL |
|---|---|---|---|---|
| **OpenWeatherMap** | Current + historical weather | Global | Free tier (1K/day) | openweathermap.org |
| **WeatherAPI** | Historical weather | Global | Free tier (1M/mo) | weatherapi.com |
| **NOAA** | US weather data | US | Free | noaa.gov |
| **Visual Crossing** | Historical weather | Global | Free tier | visualcrossing.com |

---

## 9. TRANSPORTATION

| Source | Data | Coverage | Format | URL |
|---|---|---|---|---|
| **Google Places API** | Points of interest | Global | Paid | maps.googleapis.com |
| **OpenStreetMap POI** | Restaurants, attractions | Global | Free | openstreetmap.org |
| **Walk Score** | Walkability, transit scores | US | API | walkscore.com |
| **FlightAware** | Flight schedules, arrivals | Global | API | flightaware.com |
| **ADS-B Exchange** | Real-time flight data | Global | Free | adsbexchange.com |

---

## 10. STR REGULATIONS

| Source | Data | Coverage | Format |
|---|---|---|---|
| **City open data portals** | STR registration, permits | Individual cities | CSV/JSON |
| **Host Compliance** | STR regulations database | US cities | Paid |
| **AirDNA** | Regulation scores (0-100) | Global | In their data |
| **Municode** | City ordinances | US cities | Web scraping |
| **State legislature websites** | State STR laws | US states | Web scraping |

**Known Open Data Portals:**

| City | Dataset | URL |
|---|---|---|
| **Boston** | STR Eligibility | data.boston.gov/dataset/short-term-rental-eligibility |
| **New Orleans** | STR Administration | nola.gov/next/short-term-rental-administration/ |
| **Chicago** | Various datasets | data.cityofchicago.org |
| **NYC** | STR registration | opendata.cityofnewyork.us |
| **San Francisco** | STR registration | datasf.org |
| **Los Angeles** | STR registration | data.lacity.org |

---

## 11. ML / TRAINING DATA

| Source | Data | Use Case | URL |
|---|---|---|---|
| **Inside Airbnb** | Labeled listings with reviews | Train revenue/occupancy models | insideairbnb.com |
| **Kaggle** | Various Airbnb datasets | Model training | kaggle.com |
| **Airbnb Aerosolve** | Open-source pricing model | Reference implementation | github.com/airbnb/aerosolve |
| **Academic papers** | STR pricing research | Methodology reference | arxiv.org, Google Scholar |

---

## 12. PRIORITY: What to Get First

### Week 1 (Bootstrap)
1. ✅ **Inside Airbnb** — Download CSVs for top 10 US cities
2. ✅ **Nager.Date** — Public holidays API (free, no limits)
3. ✅ **Airbnb shadow API** — Listing detail + calendar (we have this)
4. ✅ **Nominatim** — Geocoding (free)

### Week 2 (Enrich)
5. **Ticketmaster API** — Events data (free tier)
6. **US Census** — Demographics
7. **Zillow API** — Property values
8. **Google Trends** — Demand signals

### Week 3 (Scale)
9. **Booking.com GraphQL** — Hotel data (we have this)
10. **OpenWeatherMap** — Weather data
11. **OpenStreetMap** — POI data
12. **City open data portals** — STR regulations

### Week 4+ (Advanced)
13. **ATTOM Data** — Property valuations (paid)
14. **PredictHQ** — Event data (paid)
15. **Vrbo scraping** — Need residential proxies
16. **Hotel occupancy** — STR data (paid)

---

## 13. COST ESTIMATE

| Category | Free Options | Paid Options |
|---|---|---|
| **Listing data** | Inside Airbnb, our scraping | AirDNA ($20-120/mo) |
| **Calendar data** | Our scraping, Inside Airbnb | — |
| **Events** | Ticketmaster (5K/day) | PredictHQ ($$$) |
| **Holidays** | Nager.Date (unlimited) | — |
| **Geocoding** | Nominatim, Mapbox (100K/mo) | Google ($5/1K) |
| **Property values** | Zillow, RentCast | ATTOM ($95+/mo) |
| **Demographics** | US Census (free) | — |
| **Weather** | OpenWeatherMap (1K/day) | — |
| **Tourism** | UN Tourism (free) | STR (paid) |
| **Regulations** | City open data (scattered) | Host Compliance (paid) |

**Total free tier cost:** $0
**Total with paid enrichment:** $200-500/mo
