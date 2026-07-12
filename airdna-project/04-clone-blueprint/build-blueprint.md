# Build Blueprint — Rentalizer Clone

> Complete code examples for building a Rentalizer clone

---

## Data Pipeline
```
1. Scrape Airbnb/Vrbo/Booking.com daily
2. Parse listing details, pricing, availability, reviews
3. Store in time-series database
4. Calculate rolling 12-month metrics (revenue, ADR, occupancy)
5. Build market-level aggregations
6. Calculate comp scores between all listings
7. Train revenue prediction model
```

## Revenue Estimation Algorithm

```python
def estimate_revenue(address, bedrooms, bathrooms, accommodates):
    # 1. Geocode address to lat/lng
    lat, lng = geocode(address)
    
    # 2. Find comparable listings
    comps = find_comps(
        lat, lng, radius_meters=1500,
        filters={
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'accommodates': accommodates,
            'listing_type': 'entire_place'
        }
    )
    
    # 3. Score each comp
    for comp in comps:
        comp.score = calculate_comp_score(comp, target)
    
    # 4. Weighted average of comp metrics
    weights = [c.score for c in comps]
    adr = weighted_average([c.adr for c in comps], weights)
    occupancy = weighted_average([c.occupancy for c in comps], weights)
    
    # 5. Calculate monthly revenue
    monthly_revenue = adr * occupancy * days_in_month
    
    # 6. Apply seasonal adjustments
    seasonal_factors = get_seasonal_factors(market_id)
    monthly_estimates = [
        monthly_revenue * seasonal_factors[month]
        for month in range(12)
    ]
    
    # 7. Calculate confidence intervals
    revenue_lower = monthly_revenue * 0.95
    revenue_upper = monthly_revenue * 1.05
    
    # 8. Annual estimate
    annual_revenue = sum(monthly_estimates)
    
    return {
        'adr': adr,
        'occupancy': occupancy,
        'monthly_revenue': monthly_estimates,
        'annual_revenue': annual_revenue,
        'confidence': (revenue_lower, revenue_upper),
        'comps': comps
    }
```

## Comp Score Algorithm

```python
def calculate_comp_score(comp, target):
    score = 100
    
    # Geographic distance penalty
    distance = haversine(comp.location, target.location)
    score -= distance / 50  # -2 points per km
    
    # Bedroom match
    if comp.bedrooms != target.bedrooms:
        score -= 15
    
    # Bathroom match
    if comp.bathrooms != target.bathrooms:
        score -= 10
    
    # Accommodates match
    if comp.accommodates != target.accommodates:
        score -= 10
    
    # Property type match
    if comp.property_type != target.property_type:
        score -= 10
    
    # Listing type match
    if comp.listing_type != target.listing_type:
        score -= 15
    
    # Rating similarity
    rating_diff = abs(comp.rating - target.rating)
    score -= rating_diff * 5
    
    return max(0, min(100, score))
```

## Smart Rates Algorithm

```python
def calculate_smart_rates(listing_id, strategy, num_months):
    # 1. Get base rate from comps
    comps = get_comps(listing_id)
    base_rate = calculate_base_rate(comps, strategy)
    
    # 2. Get seasonal factors
    market_id = get_market(listing_id)
    seasonal = get_seasonal_factors(market_id, num_months)
    
    # 3. Get demand scores
    demand = get_demand_scores(market_id, num_months)
    
    # 4. Get day-of-week factors
    dow_factors = get_day_of_week_factors(market_id)
    
    # 5. Apply all modifiers
    rates = []
    for date in date_range(num_months):
        rate = base_rate
        rate *= seasonal[date]          # Seasonality
        rate *= demand[date]            # Demand score
        rate *= dow_factors[date.weekday()]  # Day of week
        rate *= orphan_modifier(date)   # Orphan days
        rate *= holiday_modifier(date)  # Holidays/events
        
        rates.append({
            'date': date,
            'rate': round(rate),
            'attribution': {
                'seasonality': seasonal[date],
                'demand_score': demand[date],
                'day_of_week': dow_factors[date.weekday()],
                'orphan': orphan_modifier(date),
                'holiday_or_event': holiday_modifier(date),
                'lead_time': lead_time_modifier(date)
            }
        })
    
    return rates
```

## Technology Stack

### Backend
- **Database**: PostgreSQL + TimescaleDB (time-series metrics)
- **Cache**: Redis (API responses, session data)
- **Queue**: Celery + Redis (scraping jobs, data processing)
- **API**: FastAPI or Express.js
- **Geocoding**: Google Maps API or Mapbox Geocoding
- **Maps**: Mapbox GL JS

### Data Collection
- **Scraping**: Scrapy + Scrapling (anti-bot bypass)
- **Scheduling**: Celery Beat or Airflow
- **Storage**: S3 for raw data, PostgreSQL for processed

### Frontend
- **Framework**: React + Vite
- **Maps**: Mapbox GL JS
- **Charts**: Recharts or Chart.js
- **UI**: Tailwind CSS + Radix UI

### ML/Analytics
- **Revenue Prediction**: XGBoost or LightGBM
- **Comp Scoring**: Custom similarity algorithm
- **Seasonality**: STL decomposition or Prophet
- **Demand Forecasting**: Time-series models

## Key Metrics Definitions

| Metric | Definition | Formula |
|---|---|---|
| **Revenue** | Total revenue (LTM) | Sum of all booking amounts |
| **ADR** | Average Daily Rate | Revenue / Days Reserved |
| **Occupancy** | Occupancy Rate | Days Reserved / Days Available |
| **RevPAR** | Revenue Per Available Room | Revenue / Days Available |
| **Revenue Potential** | Max possible revenue | ADR × Days Available |
| **Market Score** | Composite market score | f(demand, growth, seasonality, regulation) |
| **Comp Score** | Listing similarity score | f(distance, bedrooms, bathrooms, type, rating) |
| **Investability** | Investment attractiveness | 0-100 score |
| **Rental Demand** | Demand level | 0-100 score |
| **Revenue Growth** | Growth trend | 0-100 score |
| **Seasonality** | Seasonal variation | 0-100 score |
| **Regulation** | Regulatory environment | 0-100 score |
