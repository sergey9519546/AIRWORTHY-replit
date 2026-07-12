# Cross-Platform Property Matching

> How to identify the same property across Airbnb, Vrbo, Booking.com

---

## The Problem
Same physical property listed on multiple platforms with:
- Different IDs
- Different titles/descriptions
- Different photos
- Slightly different metadata (beds, baths may differ)
- Different coordinates (offset by 100-500m sometimes)

## Solution: Multi-Signal Matching

### Signal 1: Geographic Proximity (40% weight)
Strongest signal. Same property = nearly identical coordinates.

```python
distance = haversine(airbnb.lat, airbnb.lng, vrbo.lat, vrbo.lng)
if distance < 0.05:    # ~50 meters
    score += 0.40
elif distance < 0.1:   # ~100 meters
    score += 0.30
elif distance < 0.5:   # ~500 meters
    score += 0.15
```

### Signal 2: Property Type (15% weight)
```python
if airbnb.type == vrbo.type:  # entire_home, private_room, etc.
    score += 0.15
```

### Signal 3: Capacity Match (20% weight)
```python
bed_match = 1 - abs(a.bedrooms - v.bedrooms) / max(a.bedrooms, v.bedrooms, 1)
bath_match = 1 - abs(a.bathrooms - v.bathrooms) / max(a.bathrooms, v.bathrooms, 1)
guest_match = 1 - abs(a.max_guests - v.max_guests) / max(a.max_guests, v.max_guests, 1)
score += 0.20 * (bed_match + bath_match + guest_match) / 3
```

### Signal 4: Photo Perceptual Hashing (15% weight)
```python
from PIL import Image
import imagehash

def compare_photos(photos_a, photos_b):
    hashes_a = [imagehash.phash(Image.open(url)) for url in photos_a[:5]]
    hashes_b = [imagehash.phash(Image.open(url)) for url in photos_b[:5]]
    
    matches = 0
    for ha in hashes_a:
        for hb in hashes_b:
            if ha - hb < 10:  # Hamming distance threshold
                matches += 1
                break
    
    return matches / min(len(hashes_a), len(hashes_b))
```

### Signal 5: Title/Description Fuzzy Match (10% weight)
```python
from rapidfuzz import fuzz

title_sim = fuzz.ratio(airbnb.title.lower(), vrbo.title.lower()) / 100
score += 0.10 * title_sim
```

## Threshold
- Score > 0.65 = same property (high confidence)
- Score 0.50-0.65 = possible match (needs review)
- Score < 0.50 = different property

## Tools
- **rapidfuzz** — fast fuzzy string matching
- **imagehash** — perceptual photo hashing
- **libpostal** — address parsing/normalization
- **PostGIS** — geospatial queries

## Cross-OTA Booking Deduction
Once properties are matched:
- Vrbo bookings show as blocked dates on Airbnb
- If Airbnb calendar shows blocked AND Vrbo shows booked = confirmed booking
- Increases booking detection accuracy significantly
