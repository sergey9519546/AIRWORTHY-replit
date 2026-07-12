# Revenue Estimation (Rentalizer Clone)

> How to estimate revenue for any property using comparable listings

---

## Formula

```
Revenue = Weighted_Avg(comp_revenues) × seasonality × demand_growth
```

## Step 1: Find Comps
- Radius: 10 miles (15km) from target property
- Filter: active listings with bookings in trailing 12 months

## Step 2: Score Similarity

| Factor | Weight | Scoring |
|---|---|---|
| Distance | 35% | 1 - (miles / 10) |
| Bedrooms | 25% | 1 - abs(diff) / max(target, 1) |
| Bathrooms | 15% | 1 - abs(diff) / max(target, 1) |
| Guest capacity | 15% | 1 - abs(diff) / max(target, 1) |
| Property type | 10% | Same = 1.0, different = 0.3 |

## Step 3: Weighted Average

```python
def estimate_revenue(target, comps):
    total_weight = 0
    weighted_rev = 0
    
    for comp in comps:
        weight = comp.similarity_score
        weighted_rev += comp.annual_revenue * weight
        total_weight += weight
    
    base_estimate = weighted_rev / total_weight
    
    # Apply market adjustments
    market = get_market(target.market_id)
    adjusted = base_estimate * (1 + market.revenue_growth_yoy)
    adjusted *= market.seasonality_factor(target.month)
    
    return adjusted
```

## Step 4: Confidence Score

```python
def confidence(comps):
    revenues = [c.annual_revenue for c in comps]
    cv = std(revenues) / mean(revenues)  # Coefficient of variation
    
    if cv < 0.25: return "high"
    if cv < 0.50: return "medium"
    return "low"
```

## What AirDNA's Rentalizer Returns
- Projected annual revenue
- Projected occupancy rate
- Projected ADR
- Comp set (list of comparable listings)
- Comp set strength (confidence)
- Revenue range (min/max)
- Monthly breakdown

## Limitations
- Can't capture property condition/quality
- Ignores host skill, response time
- No data on unique features (views, hot tubs)
- Sparse markets = poor comps = bad estimates
