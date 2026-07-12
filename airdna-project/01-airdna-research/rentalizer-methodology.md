# Rentalizer Methodology

> How AirDNA estimates revenue for any property

---

## From AirDNA's Official Help Docs

> "Our algorithm searches for comparable properties within a **10-mile (15km) radius**. Properties are selected based on **proximity** and **similarities in bedroom, bathroom, and guest count**. A **weighted average** of these properties' historical performance gives you an estimate. We also factor in **seasonality, rental demand, and revenue growth**."

## How It Works (Step by Step)

### Step 1: Geocode the Address
- Convert address → lat/lng coordinates
- Identify market and submarket

### Step 2: Find Comps
- Search radius: 10 miles (15km)
- Filter by: bedrooms, bathrooms, guest capacity
- Must be active listings (had bookings in trailing 12 months)

### Step 3: Score Comps
Similarity score based on:
- **Proximity** (35% weight) — closer = better
- **Bedroom match** (25%) — exact match = 1.0
- **Bathroom match** (15%) — exact match = 1.0
- **Guest capacity** (15%) — exact match = 1.0
- **Property type** (10%) — same type = 1.0

### Step 4: Weighted Average
```
estimated_revenue = Σ(comp_revenue × similarity_score) / Σ(similarity_score)
```

### Step 5: Market Adjustments
- **Seasonality** — adjust for time of year
- **Revenue growth** — YoY market trend
- **Rental demand** — booking velocity

### Step 6: Confidence Score
Based on revenue variance among comps:
- **High:** CV < 0.25 (comps agree)
- **Medium:** CV 0.25-0.50
- **Low:** CV > 0.50 (comps disagree wildly)

## What Rentalizer Returns

| Metric | Description |
|---|---|
| Projected Revenue | Annual revenue estimate (next 12 months) |
| Projected Occupancy | Estimated occupancy rate |
| Projected ADR | Estimated average daily rate |
| Comp Set | List of comparable listings used |
| Comp Set Strength | Confidence score (Low/Medium/High) |
| Revenue Range | Min/max from comp set |
| Monthly Breakdown | Revenue projection by month |

## What It Doesn't Account For
- Property condition / interior quality
- Host skill / response time
- Unique features (views, hot tubs, pools)
- Listing quality (photos, description)
- Pricing strategy
- Recent renovations

## Comp Set Customization
Users can:
- Add/remove specific comps
- Adjust bedroom/bathroom/guest count
- See comp details (ADR, occupancy, revenue, reviews)
