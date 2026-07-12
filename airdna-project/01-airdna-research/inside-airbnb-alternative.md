# Inside Airbnb — The Open-Source Alternative

> Free, academic-grade Airbnb data for 100+ cities

---

## Overview
- **URL:** https://insideairbnb.com/
- **Creator:** Murray Cox (independent activist/researcher)
- **License:** Creative Commons Attribution 4.0 International
- **Data:** Airbnb-only (no Vrbo, no Booking.com)
- **Coverage:** 100+ cities worldwide
- **Update frequency:** Quarterly (last 12 months available free)

## Data Files Available Per City

| File | Description |
|---|---|
| `listings.csv.gz` | Detailed listings data |
| `calendar.csv.gz` | Detailed calendar data |
| `reviews.csv.gz` | Detailed review data |
| `listings.csv` | Summary info + metrics (visualization-ready) |
| `reviews.csv` | Summary review data |
| `neighbourhoods.csv` | Neighbourhood list for geo filtering |
| `neighbourhoods.geojson` | GeoJSON polygons |

## Regional Archives
Australia, Canada, France, Germany, Greece, Italy, Netherlands, Portugal, Spain, Sweden, UK, US

## Key Differences from AirDNA

| Aspect | Inside Airbnb | AirDNA |
|---|---|---|
| Data source | Airbnb only | Airbnb + Vrbo + Booking.com |
| Revenue model | None (raw data only) | Full revenue estimation |
| Deduplication | None | Cross-platform matching |
| Occupancy | Calendar-based estimates | ML-based reservation detection |
| Update frequency | Quarterly | Daily |
| Cost | Free (CC BY 4.0) | Free tier + paid plans |
| API | None | Full enterprise API |
| Scope | 100+ cities | 120K+ markets globally |

## How to Use InsideAirbnb Data

> Note: Direct CSV download URLs may require browser access. Use the website to download.

```python
import pandas as pd

# Download from insideairbnb.com/get-the-data/ via browser
# Direct URLs may return 403 — use browser download or requests with proper headers
listings = pd.read_csv('listings.csv.gz')
calendar = pd.read_csv('calendar.csv.gz')
reviews = pd.read_csv('reviews.csv.gz')

# Calendar-based occupancy estimation
calendar['available'] = calendar['available'].map({'t': True, 'f': False})
calendar['price'] = calendar['price'].str.replace('$', '').str.replace(',', '').astype(float)

# Per-listing occupancy
occupancy = calendar.groupby('listing_id')['available'].mean()
occupancy_rate = 1 - occupancy  # unavailable = booked

# Revenue estimation
booked = calendar[~calendar['available']]
revenue = booked.groupby('listing_id')['price'].sum()
```

## Other Free/Open Alternatives

| Source | Data | Coverage |
|---|---|---|
| **InsideAirbnb** | Listings, calendar, reviews | 100+ cities, quarterly |
| **Tom Slee** | Historical Airbnb data CSVs | 2013-2017, S3 downloads |
| **AirDNA Free Tier** | Basic market stats | Global, limited |
| **InsideBnb** | ZIP-level revenue/occupancy | Global, $5.99/market |
| **Airbtics** | Alternative to AirDNA | Global, paid |

## Bootstrap Strategy
Use InsideAirbnb historical data to:
1. Train booking detection models
2. Validate occupancy estimates
3. Build initial market baselines
4. Test comp selection algorithms
5. Calibrate revenue estimation
