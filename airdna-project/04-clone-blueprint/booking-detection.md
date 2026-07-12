# Booking Detection Algorithm

> The core piece — how to infer real bookings from calendar data

---

## The Problem
Airbnb calendars show dates as "unavailable" but don't say why:
- Real booking ✓
- Host blocked (personal use, maintenance) ✗
- Pricing strategy (priced too high) ✗
- Minimum stay requirement ✗

## The Solution: Calendar Diff + Heuristic Scoring

Reconstructed from industry knowledge, HBS case study references, and calendar data analysis. AirDNA uses something similar but won't disclose it. PriceLabs uses a similar approach but hasn't published their algorithm.

## Data Required
Daily calendar snapshots per listing:
```
listing_id | date       | available | price  | scraped_at
12345      | 2026-07-01 | true      | $250   | 2026-06-28
12345      | 2026-07-02 | false     | $250   | 2026-06-28
12345      | 2026-07-03 | false     | $250   | 2026-06-28
```

## Algorithm

### Step 1: Calendar Diff
Compare consecutive daily snapshots for each listing:

```python
def detect_changes(yesterday, today):
    """Find dates that flipped available→unavailable."""
    changes = []
    for date in all_dates:
        if yesterday[date] == "available" and today[date] == "unavailable":
            changes.append(date)
    return changes
```

### Step 2: Group into Stays
Consecutive unavailable dates = one stay:

```python
def group_stays(dates):
    """Group consecutive dates into stays."""
    stays = []
    current = [dates[0]]
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] + timedelta(days=1):
            current.append(dates[i])
        else:
            stays.append(current)
            current = [dates[i]]
    stays.append(current)
    return stays
```

### Step 3: Block Removal Heuristics
Score each stay on 4 factors:

```python
def booking_probability(stay, market_data):
    score = 0.0
    
    # Factor 1: Length of stay (35% weight)
    nights = len(stay)
    if 1 <= nights <= 7:
        score += 0.35      # Typical Airbnb stay
    elif 8 <= nights <= 14:
        score += 0.20
    elif nights > 14:
        score += 0.05      # Could be monthly
    
    # Factor 2: Booking window (30% weight)
    days_until = (stay[0] - today).days
    if 0 <= days_until <= 30:
        score += 0.30      # Last-minute = likely real
    elif 31 <= days_until <= 90:
        score += 0.20
    elif days_until > 180:
        score += 0.02      # Far out = likely block
    
    # Factor 3: Market correlation (20% weight)
    market_occ = market_data["occupancy_rate"]
    listing_blocked = blocked_days / 365
    if abs(market_occ - listing_blocked) < 0.15:
        score += 0.20      # Consistent with market
    
    # Factor 4: Price variation (15% weight)
    if has_dynamic_pricing(stay):
        score += 0.15      # Different prices = likely real
    
    return score  # >0.6 = likely booking
```

### Step 4: Calculate Metrics
```python
def compute_listing_metrics(listing_id, month):
    stays = get_inferred_bookings(listing_id, month)
    available = get_available_days(listing_id, month)
    
    booked_nights = sum(len(s) for s in stays if s.probability > 0.6)
    total_nights = days_in_month(month)
    
    occupancy = booked_nights / total_nights
    adr = average_price(booked_stays)
    revenue = booked_nights * adr
    
    return {"occupancy": occupancy, "adr": adr, "revenue": revenue}
```

## Database Schema

```sql
CREATE TABLE calendar_snapshots (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,
    calendar_date DATE NOT NULL,
    available BOOLEAN,
    price DECIMAL(10,2),
    currency VARCHAR(3),
    scraped_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(listing_id, calendar_date, scraped_at::date)
);

CREATE TABLE inferred_bookings (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    nights INT,
    probability FLOAT,
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE listing_monthly_metrics (
    listing_id BIGINT NOT NULL,
    month DATE NOT NULL,
    occupied_nights INT,
    available_nights INT,
    occupancy_rate FLOAT,
    adr DECIMAL(10,2),
    revenue DECIMAL(10,2),
    PRIMARY KEY (listing_id, month)
);
```

## Scraping Frequency
- **Daily** for calendar snapshots (minimum)
- **Twice daily** for high-value markets
- **Real-time** for active booking detection

## Accuracy Notes
- ~85-90% accuracy vs ground truth (per PriceLabs claims)
- Biggest error source: host blocking patterns vary wildly
- Monthly stays are hardest to classify
- Cross-OTA deduction helps (Vrbo bookings show as Airbnb blocks)
