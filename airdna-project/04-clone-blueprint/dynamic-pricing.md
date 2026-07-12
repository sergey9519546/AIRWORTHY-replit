# Dynamic Pricing Engine

> How to recommend optimal nightly rates

---

## 7 Adjustment Factors

```
Recommended Price = Base × Season × DOW × Pacing × Lead × Event × Urgency
```

### 1. Base Rate
Median ADR for comparable listings in this market

### 2. Seasonality Factor
```python
# Ratio of this month's revenue to annual average
# >1 = peak season, <1 = off season
season_factor = monthly_revenue[month] / annual_avg_revenue
```

### 3. Day of Week Factor
| Day | Factor |
|---|---|
| Monday | 0.90 |
| Tuesday | 0.92 |
| Wednesday | 0.95 |
| Thursday | 0.98 |
| Friday | 1.10 |
| Saturday | 1.15 |
| Sunday | 1.00 |

### 4. Demand Pacing
Compare booking velocity vs same period last year
```python
pacing = current_bookings / last_year_bookings
```

### 5. Lead Time Factor
| Days Until | Factor |
|---|---|
| 0-3 | 0.85 (last minute discount) |
| 4-7 | 0.92 |
| 8-30 | 1.00 |
| 31-90 | 1.02 (early bird premium) |
| 90+ | 0.98 (too far out) |

### 6. Event Detection
- Concerts, sports, conferences → price multiplier
- Use Ticketmaster API, Google Events
- Typical: 1.3x - 2.0x during major events

### 7. Occupancy Urgency
```python
next_30_occ = listing.occupancy_next_30_days
if next_30_occ < 0.3:
    urgency = 0.85  # Low occupancy → lower price
elif next_30_occ > 0.8:
    urgency = 1.10  # High occupancy → raise price
else:
    urgency = 1.00
```

## Floor/Ceiling
```python
min_price = base_rate * 0.5
max_price = base_rate * 2.5
recommended = max(min_price, min(max_price, recommended))
```

## Airbnb's Own Tool: Aerosolve
Airbnb open-sourced their ML pricing tool in 2015:
- GitHub: `github.com/airbnb/aerosolve`
- Scala-based (not Java), uses gradient boosted trees
- Features: listing attributes, location, demand signals
- 4,800+ stars, still maintained (last push Nov 2025)
- Useful as reference implementation for pricing models
