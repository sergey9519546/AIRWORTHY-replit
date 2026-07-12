# HAR File Capture Method

> How to extract data using browser DevTools + HAR export

---

## The Stevesie Method (AirDNA Data)

### Step 1: Browse AirDNA
1. Sign up for AirDNA free tier
2. Open Chrome DevTools (F12) → Network tab
3. Check "Preserve log"
4. Browse markets, listings, data you want

### Step 2: Export HAR
1. In Network tab, click ⬇️ (Export HAR)
2. Save the `.har` file

### Step 3: Parse HAR
Upload to https://stevesie.com/har-file-web-scraper or parse manually:

```python
import json

with open('airdna.har', 'r') as f:
    har = json.load(f)

api_calls = []
for entry in har['log']['entries']:
    url = entry['request']['url']
    if '/api/' in url:
        response = entry['response']['content'].get('text', '')
        if response:
            try:
                data = json.loads(response)
                api_calls.append({
                    'url': url,
                    'method': entry['request']['method'],
                    'data': data
                })
            except:
                pass

# Extract listing data
for call in api_calls:
    if 'property_list' in call['url']:
        listings = call['data'].get('properties', [])
        for listing in listings:
            print(f"{listing['title']}: ${listing.get('adr', 'N/A')}/night")
```

## What You Can Get from AirDNA's Internal API

| Endpoint | Data |
|---|---|
| `/api/v1/market/property_list` | Listing data with access_token |
| Property titles, IDs, types | ✅ |
| Bedrooms, bathrooms | ✅ |
| Revenue estimates | ✅ |
| Occupancy estimates | ✅ |
| Lat/long (approximate) | ✅ |
| Market IDs, ratings | ✅ |

## Legal Notes
- You're scraping a recording of your own browsing
- Not violating ToS (you're using the service normally)
- Don't republish the data commercially
- Internal use only

## Also Works For
- Airbnb (GraphQL endpoints captured)
- Vrbo (similar approach)
- Any SPA with API calls
