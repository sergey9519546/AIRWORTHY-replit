# Anomaly Detection & Data Cleaning

> How to filter bad data from scraped listings

---

## Multi-Stage Pipeline

### Stage 1: Price Outliers
```python
def is_valid_price(listing, market_stats):
    median_price = market_stats["median_adr"]
    
    # Flag if >3x or <0.3x market median
    if listing.adr > median_price * 3:
        return False
    if listing.adr < median_price * 0.3 and listing.adr > 0:
        return False
    if listing.adr <= 0:
        return False
    
    return True
```

### Stage 2: Fake/Inactive Detection
```python
def is_likely_fake(listing):
    # No reviews after 6+ months = likely inactive
    if listing.months_active > 6 and listing.review_count == 0:
        return True
    
    # Stock photos (image hash clustering)
    if has_stock_photos(listing.photos):
        return True
    
    # Copy-pasted descriptions
    if is_duplicate_description(listing.description, threshold=0.9):
        return True
    
    # Unreasonable capacity (e.g., 50 guests in a studio)
    if listing.max_guests > listing.bedrooms * 4 + 4:
        return True
    
    return False
```

### Stage 3: Data Quality Scoring
```python
def compute_quality_score(listing):
    score = 0
    
    # Has reviews
    if listing.review_count > 0:
        score += 0.25
    if listing.review_count >= 10:
        score += 0.10
    
    # Has rating
    if listing.rating and listing.rating > 0:
        score += 0.15
    
    # Has photos (more = better)
    photo_count = len(listing.photos or [])
    score += min(photo_count / 10, 0.15)
    
    # Has complete description
    if listing.description and len(listing.description) > 100:
        score += 0.10
    
    # Has amenities
    if listing.amenities and len(listing.amenities) > 5:
        score += 0.10
    
    # Has superhost status
    if listing.is_superhost:
        score += 0.10
    
    # Calendar activity
    if listing.calendar_updated_recently:
        score += 0.05
    
    return min(score, 1.0)
```

### Stage 4: Minimum Quality Threshold
```python
def clean_listings(listings):
    cleaned = []
    for listing in listings:
        if not is_valid_price(listing):
            continue
        if is_likely_fake(listing):
            continue
        listing.quality_score = compute_quality_score(listing)
        if listing.quality_score >= 0.3:
            cleaned.append(listing)
    return cleaned
```

## AirDNA's Approach
- Uses 5 sub-models for anomaly detection
- Model 5.0 has "stronger anomaly detection"
- Filters based on: pricing patterns, calendar behavior, review patterns
- Unknown exact thresholds

## Common Anomalies

| Anomaly | Detection |
|---|---|
| Test listing | No reviews, generic title |
| Inactive listing | No calendar updates in 90+ days |
| Overpriced | ADR > 3x market median |
| Underpriced | ADR < 0.3x market median |
| Fake reviews | Review velocity too high |
| Duplicate | Same photos/description as another listing |
| Unreasonable capacity | 50 guests in studio apartment |
