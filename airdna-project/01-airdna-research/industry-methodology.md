# Industry Revenue Estimation Methodology

> How the STR analytics industry estimates revenue

---

## Core Formula
```
Annual Revenue = ADR × Occupancy Rate × Available Nights
```

## ADR (Average Daily Rate)
- = Total Revenue ÷ Total Booked Nights (trailing 12 months)
- Includes cleaning fee, excludes OTA service fees
- Calculated per-property and aggregated at market level

## Occupancy Rate
- = Reserved Days ÷ Total Active Listing Nights
- "Active" = not blocked AND had a reservation within past 28 days
- Market level: Total nights booked ÷ Total nights available × 100

## Revenue
- = Booked Days × ADR
- Sum of nightly rates + cleaning fees - host discounts - service fees
- Market average = Total market revenue ÷ Unique booked listings

## Comp Selection (Industry Standard)
1. **Geographic proximity** — same neighborhood/submarket
2. **Property characteristics** — bedrooms, bathrooms, type, capacity
3. **Amenity similarity**
4. **Performance tier alignment**

## Historical Performance Analysis
- Trailing 12-month data preferred (smooths seasonality)
- Monthly granularity for seasonal patterns
- Revenue percentiles (25th, 50th, 75th) rather than just averages

## Adjustment Factors
1. Seasonality (monthly/weekly patterns)
2. Market trends (supply growth, demand shifts)
3. Property-specific adjustments (amenities, reviews, superhost)
4. Regulatory risk
5. Lead time and booking pace

## Key Metrics
| Metric | Definition |
|---|---|
| **ADR** | Average Daily Rate |
| **RevPAR** | Revenue Per Available Rental (= ADR × Occupancy) |
| **TRevPAR** | Total Revenue Per Available Rental (including fees) |
| **Days Available** | Calendar availability window |
| **Booking Lead Time** | How far in advance guests book |
| **Average Length of Stay** | Nights per booking |

## Known Limitations
- New listings (zero reviews) significantly underperform estimates
- Estimates skew optimistic (reflect well-managed properties)
- Thin markets with few comps produce unreliable estimates
- Dynamic pricing by hosts introduces variance
- Mid/long-term stays (30+ nights) have different economics
- Seasonal markets require month-level granularity
- Cross-platform listing duplication can inflate supply counts

## Academic References
- NIH/PMC study (2024) validates AirDNA as major STR data source
- MIT Sloan paper uses AirDNA data for tax compliance research
- Multiple forecasting papers reference AirDNA occupancy methodology
- OECD reports cite AirDNA market data
