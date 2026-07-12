# Market Aggregation

> How to roll up listing-level data into market-level metrics

---

## Core Metrics Per Market

```python
def compute_market_metrics(listings, month):
    active = [l for l in listings if is_active(l, month)]
    
    revenues = [l.monthly_revenue for l in active if l.monthly_revenue]
    adrs = [l.adr for l in active if l.adr]
    occupancies = [l.occupancy_rate for l in active if l.occupancy_rate]
    
    return {
        "active_listings": len(active),
        "median_revenue": np.median(revenues),
        "avg_revenue": np.mean(revenues),
        "median_adr": np.median(adrs),
        "avg_adr": np.mean(adrs),
        "median_occupancy": np.median(occupancies),
        "avg_occupancy": np.mean(occupancies),
        "revpar": np.mean(revenues) / 30,
        "supply_growth": compute_supply_growth(listings, month),
        "revenue_growth": compute_revenue_growth(listings, month),
        "seasonality_index": compute_seasonality(listings, month),
    }
```

## Supply Growth
```python
def compute_supply_growth(listings, month):
    current = count_active(listings, month)
    previous = count_active(listings, month - 12)
    if previous == 0:
        return 0
    return (current - previous) / previous
```

## Revenue Growth
```python
def compute_revenue_growth(listings, month):
    current = avg_revenue(listings, month)
    previous = avg_revenue(listings, month - 12)
    if previous == 0:
        return 0
    return (current - previous) / previous
```

## Seasonality Index
```python
def compute_seasonality(listings, month):
    """Ratio of this month's revenue to annual average."""
    monthly_revenues = []
    for m in range(1, 13):
        rev = np.mean([l.revenue_for_month(m) for l in listings if l.revenue_for_month(m)])
        monthly_revenues.append(rev)
    
    annual_avg = np.mean(monthly_revenues)
    if annual_avg == 0:
        return 1.0
    
    return monthly_revenues[month - 1] / annual_avg
```

## AirDNA Market Scores (0-100)

| Score | Description |
|---|---|
| investability | Investment attractiveness |
| rental_demand | Demand level |
| revenue_growth | Revenue growth trend |
| seasonality | Seasonality score |
| regulation | Regulatory environment |

## Market Types
```
urban_metro | mountains_lakes | coastal | suburban | rural | mid_size_city
```

## Database Views

```sql
CREATE MATERIALIZED VIEW market_monthly AS
SELECT
    market_id,
    DATE_TRUNC('month', month) AS month,
    COUNT(*) AS active_listings,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenue) AS median_revenue,
    AVG(revenue) AS avg_revenue,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY adr) AS median_adr,
    AVG(adr) AS avg_adr,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY occupancy_rate) AS median_occupancy,
    AVG(occupancy_rate) AS avg_occupancy
FROM listing_monthly_metrics
WHERE revenue > 0
GROUP BY market_id, DATE_TRUNC('month', month);
```

## Submarket Granularity
- AirDNA provides submarket-level data
- ZIP-code level (InsideBnb does this)
- Neighborhood-level where available
