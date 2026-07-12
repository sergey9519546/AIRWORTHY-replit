# Smart Rates Attribution System

> How AirDNA's dynamic pricing works — full detail from API

---

## Architecture (Adapt — 4 Layers)

1. **Data Layer** — 15M listings tracked daily, 1TB+ data/day, 10+ years historical
2. **Model Layer** — ML team (Denver, Atlanta, SF), advanced degrees, decade of historical + pacing data
3. **Adjustment Layer** — Preset playbooks based on goals, fully customizable
4. **AI Layer** — Makes pricing easier to implement, explain, adjust (natural language interface)

## Three Pricing Strategies

| Strategy | Goal |
|---|---|
| **High ADR** | Maximize average daily rate |
| **High Occupancy** | Maximize occupancy |
| **Balanced** | Optimize balance between ADR and Occupancy |
| **Custom** | User provides own base rate with modifiers |

## Base Rate Calculation

**Requirements:**
- At least 5 reserved days with valid price in last year
- At least 5 comps with 15+ days reserved in last year
- City must have 50+ reserved nights in last year

**If requirements not met:** Base rate cannot be generated

## Daily Rate Formula

```
Daily Rate = Base Rate × (1 + sum of modifiers)
```

## Modifier Types

| Modifier | Range | Description |
|---|---|---|
| **Demand Score** | -1.0 to +1.0 | Real-time demand signal |
| **Holiday/Event** | 0 to +1.0 | Premium for holidays and local events |
| **Lead Time** | -0.5 to +0.5 | How far in advance the booking is |
| **Orphan** | -0.3 to 0 | Discount for isolated single nights |
| **Seasonality** | -0.5 to +0.5 | Monthly/seasonal patterns |
| **Day of Week** | -0.2 to +0.2 | Weekday vs weekend pricing |

## Orphan Day Modifiers
Built-in support for 1-day and 2-day orphan gap pricing:
- Single orphan day between bookings: up to -30% discount
- Two-day orphan gap: up to -20% discount

## Smart Rates API Endpoints

```
GET  /listing/{id}/smart_rates/pricing_strategies — Base rates per strategy
POST /listing/{id}/smart_rates                   — Daily recommended rates
```

## Response Format
```json
{
  "rates": [
    {
      "date": "2024-01-01",
      "rate": 120,
      "attribution": {
        "demand_score": 0.15,
        "holiday_or_event": 0.0,
        "lead_time": -0.05,
        "orphan": -0.3,
        "seasonality": 0.1,
        "day_of_week": 0.05
      }
    }
  ]
}
```

## Competitors
- **PriceLabs** — Market leader in dynamic pricing (~$20/listing/mo)
- **Beyond Pricing** (now Beyond) — Pioneer in STR pricing (3-5% of revenue)
- **Wheelhouse** — AI-powered pricing (3-5% of revenue)
- **Guesty Revenue Management** — Part of PMS suite

## Key Insight
Jamie Lane (Chief Economist): "69% of listings are exclusive to a single OTA" — this shapes how Adapt builds its pricing model, needing cross-platform visibility.
