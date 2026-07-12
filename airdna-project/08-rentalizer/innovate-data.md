# Data Innovations for Rentalizer v2

**Author:** Senior Data Engineer
**Date:** 2026-06-29
**Scope:** 10 concrete innovations to fix leakage, add predictive signal, and build a scalable data architecture

---

## Innovation 1: Remove Leaky Features, Add Real Predictive Features

### Problem

The current model achieves R²=0.997 by cheating. Sixty-five percent of feature importance comes from features that are direct consequences of the target variable (`reviews_ltm`, `availability_365`, etc.). At inference time, these features are zeroed out, rendering the model useless for its actual purpose — predicting revenue for *new* listings.

### Solution

Strip all leaky features and replace them with pre-outcome listing characteristics that are known *before* a listing earns revenue.

**Remove (leaky):**
- `reviews_ltm`, `reviews_per_month_num`, `reviews_total`, `review_recency_days`, `reviews_ltm_ratio`
- `availability_365_num`, `availability_30_num`, `occupancy_proxy`
- `review_score` (post-outcome — only exists after guests stay)

**Add (pre-outcome):**
- `host_response_rate` (0–1 float)
- `host_response_time` (categorical: within an hour, within a few hours, within a day, a few days or more)
- `host_acceptance_rate` (0–1 float)
- `num_amenities` (count)
- `amenity_wifi`, `amenity_kitchen`, `amenity_washer`, `amenity_dryer`, `amenity_ac`, `amenity_heating`, `amenity_tv` (binary flags for top amenities)
- `has_house_rules` (binary)
- `cancellation_policy` (categorical: flexible, moderate, strict)
- `photo_count` (integer)
- `description_length` (word count — proxy for effort)
- `host_total_listings_count` (professional vs. casual host)
- `room_type_detail` (property_type from source data, properly cleaned)

### Code

```python
# In prepare_data.py — engineer_features() replacement

def engineer_features_v2(df):
    """Create non-leaky features for revenue prediction."""

    # === NUMERIC (from listing attributes, not outcomes) ===
    df["accommodates_num"] = pd.to_numeric(df["accommodates"], errors="coerce").fillna(2)
    df["bedrooms_num"] = pd.to_numeric(df["bedrooms"], errors="coerce").fillna(0)
    df["bathrooms_num"] = pd.to_numeric(df.get("bathrooms"), errors="coerce").fillna(1)
    df["beds_num"] = pd.to_numeric(df.get("beds"), errors="coerce").fillna(
        df["accommodates_num"] / 2
    )
    df["minimum_nights_num"] = pd.to_numeric(df["minimum_nights"], errors="coerce").fillna(1)
    df["price_num"] = pd.to_numeric(
        df["price"].astype(str).str.replace("$", "").str.replace(",", ""),
        errors="coerce"
    )

    # Host attributes (pre-outcome)
    df["host_listings_count_num"] = pd.to_numeric(
        df.get("host_total_listings_count"), errors="coerce"
    ).fillna(1)
    df["host_experience_months"] = compute_months_since(df, "host_since")
    df["instant_bookable_num"] = (df.get("instant_bookable") == "t").astype(int)
    df["superhost_num"] = (df.get("host_is_superhost") == "t").astype(int)

    # Host response metrics
    df["host_response_rate_num"] = (
        df.get("host_response_rate", pd.Series(dtype=str))
        .astype(str).str.replace("%", "")
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0) / 100.0
    )
    df["host_acceptance_rate_num"] = (
        df.get("host_acceptance_rate", pd.Series(dtype=str))
        .astype(str).str.replace("%", "")
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0) / 100.0
    )
    response_time_map = {
        "within an hour": 1,
        "within a few hours": 2,
        "within a day": 3,
        "a few days or more": 4,
    }
    df["host_response_time_num"] = (
        df.get("host_response_time", pd.Series(dtype=str))
        .str.lower().map(response_time_map).fillna(3)
    )

    # Listing quality proxies
    df["description_length"] = (
        df.get("description", pd.Series(dtype=str))
        .fillna("").str.split().str.len()
    )
    df["photo_count"] = pd.to_numeric(
        df.get("picture_count", df.get("number_of_photos")), errors="coerce"
    ).fillna(0)
    df["num_amenities"] = (
        df.get("amenities", pd.Series(dtype=str))
        .fillna("[]").str.count(",") + 1
    )

    # Top amenity flags
    amenities_col = df.get("amenities", pd.Series(dtype=str)).fillna("[]").str.lower()
    for amenity, pattern in [
        ("wifi", "wifi"), ("kitchen", "kitchen"), ("washer", "washer"),
        ("dryer", "dryer"), ("ac", "air conditioning"), ("heating", "heating"),
        ("tv", '"tv"'), ("elevator", "elevator"), ("gym", "gym"),
        ("pool", "pool"), ("balcony", "balcony"), ("parking", "parking"),
    ]:
        df[f"amenity_{amenity}"] = amenities_col.str.contains(pattern, na=False).astype(int)

    # Cancellation policy
    df["cancellation_policy"] = df.get("cancellation_policy", "moderate").fillna("moderate")

    # Has house rules
    df["has_house_rules"] = (
        df.get("house_rules", pd.Series(dtype=str)).fillna("").str.len() > 0
    ).astype(int)

    # Derived
    df["price_per_person"] = df["price_num"] / df["accommodates_num"].clip(lower=1)
    df["beds_per_person"] = df["beds_num"] / df["accommodates_num"].clip(lower=1)
    df["bath_to_bed_ratio"] = df["bathrooms_num"] / df["bedrooms_num"].clip(lower=1)

    # Borough
    borough_col = "neighbourhood_group_cleansed"
    df["borough"] = df[borough_col].fillna("Unknown") if borough_col in df.columns else "Unknown"

    # Property type
    if "property_type" in df.columns:
        prop_counts = df["property_type"].value_counts()
        rare = prop_counts[prop_counts < 20].index
        df["property_type_clean"] = df["property_type"].replace(rare, "Other")
    else:
        df["property_type_clean"] = "Unknown"

    # Target
    df["log_revenue"] = np.log1p(df["revenue"])

    return df


def get_feature_columns_v2():
    """Non-leaky feature columns."""
    return [
        # Listing attributes
        "price_num", "accommodates_num", "bedrooms_num", "bathrooms_num",
        "beds_num", "minimum_nights_num",
        # Host attributes
        "host_listings_count_num", "host_experience_months",
        "host_response_rate_num", "host_acceptance_rate_num", "host_response_time_num",
        "instant_bookable_num", "superhost_num",
        # Listing quality
        "description_length", "photo_count", "num_amenities",
        "has_house_rules",
        # Top amenities
        "amenity_wifi", "amenity_kitchen", "amenity_washer", "amenity_dryer",
        "amenity_ac", "amenity_heating", "amenity_tv", "amenity_elevator",
        "amenity_gym", "amenity_pool", "amenity_balcony", "amenity_parking",
        # Derived
        "price_per_person", "beds_per_person", "bath_to_bed_ratio",
        # Location
        "latitude", "longitude",
    ]
```

### Expected Impact

R² will drop from 0.997 to **0.35–0.50**. This is the honest baseline. From here, Innovations 2–9 will push it back toward 0.60–0.75 — genuine predictive power.

---

## Innovation 2: Subway/Transit Distance (MTA Data)

### Rationale

NYC STR demand is heavily driven by transit access. A listing 2 blocks from a subway stop commands a 15–25% premium over one 10 blocks away. The current model uses raw lat/lng, which doesn't capture this.

### Data Source

**MTA GTFS Feed** — Free, no API key required.
- URL: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs`
- Static schedule + stop locations: `https://transitfeeds.com/p/mta/89`
- Alternative: MTA subway station coordinates from NYC Open Data
  - `https://data.cityofnewyork.us/api/views/kk4q-3rt2/rows.csv`

### Architecture

```python
# src/transit_features.py

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

class TransitFeatureBuilder:
    """Compute transit proximity features for NYC listings."""

    def __init__(self, stations_path: str = None):
        if stations_path:
            self.stations = pd.read_csv(stations_path)
        else:
            self.stations = self._load_mta_stations()
        self.tree = None
        self._build_tree()

    def _load_mta_stations(self) -> pd.DataFrame:
        """Load NYC subway station data from NYC Open Data."""
        url = "https://data.cityofnewyork.us/api/views/kk4q-3rt2/rows.csv"
        df = pd.read_csv(url)
        # Columns: Station Name, Latitude, Longitude, Line, Borough
        return df.rename(columns={
            "Station Name": "name",
            "Latitude": "lat",
            "Longitude": "lng",
            "Line": "line",
            "Borough": "borough",
        })

    def _build_tree(self):
        """Build KD-Tree for fast nearest-station lookup."""
        coords = self.stations[["lat", "lng"]].values
        # Convert lat/lng to approximate meters (for NYC: 1 deg lat ≈ 111km, 1 deg lng ≈ 85km)
        self.coords_m = np.column_stack([
            coords[:, 0] * 111_000,
            coords[:, 1] * 85_000,
        ])
        self.tree = cKDTree(self.coords_m)

    def compute_features(self, lat: float, lng: float) -> dict:
        """For a single listing, compute transit features."""
        point_m = np.array([lat * 111_000, lng * 85_000])

        # Distance to nearest station (meters)
        dist, idx = self.tree.query(point_m, k=1)
        nearest = self.stations.iloc[idx]

        # Distance to 3 nearest stations (average = transit density proxy)
        dists, indices = self.tree.query(point_m, k=min(5, len(self.stations)))

        return {
            "dist_to_subway_m": float(dist),
            "dist_to_subway_km": float(dist / 1000),
            "nearest_station_name": nearest["name"],
            "nearest_station_lines": nearest.get("line", "unknown"),
            "subway_within_200m": int(dist < 200),
            "subway_within_400m": int(dist < 400),
            "subway_within_800m": int(dist < 800),
            "avg_dist_5_nearest_m": float(np.mean(dists)),
            "transit_density_1km": int(np.sum(dists < 1000)),  # stations within 1km
        }

    def batch_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add transit features to a DataFrame of listings."""
        features = df.apply(
            lambda row: self.compute_features(row["latitude"], row["longitude"]),
            axis=1,
        )
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Integration into prepare_data.py

```python
from src.transit_features import TransitFeatureBuilder

# After engineer_features_v2():
transit_builder = TransitFeatureBuilder()
df = transit_builder.batch_compute(df)

# Add to feature list:
TRANSIT_FEATURES = [
    "dist_to_subway_km", "subway_within_200m",
    "subway_within_400m", "transit_density_1km",
]
```

### Expected Impact

+3–5% R² improvement. `dist_to_subway_km` and `transit_density_1km` should be top-10 features. The binary `subway_within_400m` captures the "walk to subway" threshold that matters to guests.

---

## Innovation 3: Event Data (Ticketmaster API)

### Rationale

NYC events (concerts, sports, Broadway) drive demand spikes. A listing near MSG during a Knicks playoff game or near Broadway during fashion week sees 2–3x normal occupancy. Current model has zero event awareness.

### Data Source

**Ticketmaster Discovery API** — Free tier: 5,000 calls/day
- Docs: `https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/`
- No OAuth required, just API key
- Endpoints: `/events`, `/events/{id}`, `/attractions`, `/venues`

### Architecture

```python
# src/event_features.py

import requests
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache

class EventFeatureBuilder:
    """Compute event density features for NYC listings."""

    BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

    # NYC bounding box
    NYC_LAT, NYC_LNG = 40.7128, -74.0060
    RADIUS_MILES = 50

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_events(
        self,
        start_date: str,
        end_date: str,
        lat: float = NYC_LAT,
        lng: float = NYC_LNG,
        radius: int = RADIUS_MILES,
    ) -> pd.DataFrame:
        """Fetch all NYC events in a date range."""
        events = []
        page = 0

        while True:
            params = {
                "apikey": self.api_key,
                "latlong": f"{lat},{lng}",
                "radius": radius,
                "unit": "miles",
                "startDateTime": f"{start_date}T00:00:00Z",
                "endDateTime": f"{end_date}T23:59:59Z",
                "size": 200,
                "page": page,
                "sort": "date,asc",
            }
            resp = requests.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            page_events = data.get("_embedded", {}).get("events", [])
            if not page_events:
                break

            for e in page_events:
                venue = e.get("_embedded", {}).get("venues", [{}])[0]
                events.append({
                    "event_id": e["id"],
                    "name": e["name"],
                    "date": e["dates"]["start"].get("localDate"),
                    "type": e.get("type", "unknown"),
                    "segment": e.get("classifications", [{}])[0].get("segment", {}).get("name", ""),
                    "genre": e.get("classifications", [{}])[0].get("genre", {}).get("name", ""),
                    "venue_name": venue.get("name", ""),
                    "venue_lat": float(venue.get("location", {}).get("latitude", 0)),
                    "venue_lng": float(venue.get("location", {}).get("longitude", 0)),
                    "venue_capacity": venue.get("capacity", 0),
                })

            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

        return pd.DataFrame(events)

    def compute_listing_event_features(
        self,
        lat: float,
        lng: float,
        date: str,
        events_df: pd.DataFrame,
        lookback_days: int = 30,
    ) -> dict:
        """Compute event features for a listing on a given date."""
        from scipy.spatial import cKDTree

        target_date = pd.Timestamp(date)
        window_start = target_date - timedelta(days=lookback_days)
        window_end = target_date + timedelta(days=lookback_days)

        # Filter events in time window
        events_df["date_ts"] = pd.to_datetime(events_df["date"])
        window_events = events_df[
            (events_df["date_ts"] >= window_start) &
            (events_df["date_ts"] <= window_end)
        ]

        if len(window_events) == 0:
            return {
                "events_within_5km_30d": 0,
                "events_within_10km_30d": 0,
                "events_within_5km_7d": 0,
                "major_events_30d": 0,
                "closest_event_km": 999,
                "event_capacity_sum_30d": 0,
            }

        # Distance from listing to each event venue
        event_coords = window_events[["venue_lat", "venue_lng"]].values
        listing_coord = np.array([[lat, lng]])

        # Haversine distance in km
        from math import radians, sin, cos, sqrt, atan2
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))

        distances = [
            haversine(lat, lng, elat, elng)
            for elat, elng in event_coords
        ]
        window_events = window_events.copy()
        window_events["dist_km"] = distances

        # 7-day window
        week_events = window_events[
            (window_events["date_ts"] >= target_date - timedelta(days=7)) &
            (window_events["date_ts"] <= target_date + timedelta(days=7))
        ]

        # Major events (capacity > 5000 or segment in Music/Sports/Theater)
        major = window_events[
            (window_events["venue_capacity"] > 5000) |
            (window_events["segment"].isin(["Music", "Sports", "Arts & Theatre"]))
        ]

        return {
            "events_within_5km_30d": int((window_events["dist_km"] <= 5).sum()),
            "events_within_10km_30d": int((window_events["dist_km"] <= 10).sum()),
            "events_within_5km_7d": int((week_events["dist_km"] <= 5).sum()),
            "major_events_30d": len(major),
            "closest_event_km": float(min(distances)) if distances else 999,
            "event_capacity_sum_30d": int(
                window_events.loc[window_events["dist_km"] <= 10, "venue_capacity"].sum()
            ),
        }
```

### Offline Pipeline

Since the API has a 5K/day limit, run a batch fetch monthly and cache to Parquet:

```python
# scripts/fetch_events.py
"""Monthly cron: fetch NYC events for the next 60 days."""

import os
from datetime import datetime, timedelta
from src.event_features import EventFeatureBuilder

API_KEY = os.environ["TICKETMASTER_API_KEY"]
builder = EventFeatureBuilder(API_KEY)

start = datetime.now().strftime("%Y-%m-%d")
end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

events = builder.fetch_events(start, end)
out_path = os.path.join("data", "events", f"nyc_events_{start}.parquet")
events.to_parquet(out_path, index=False)
print(f"Saved {len(events)} events to {out_path}")
```

### Expected Impact

+2–4% R² improvement. Event features are especially valuable for short-term predictions and for listings near Midtown/Brooklyn event venues.

---

## Innovation 4: Holiday Data (Nager.Date)

### Rationale

NYC STR revenue has strong holiday effects: Thanksgiving, Christmas/New Year, July 4th, Labor Day weekend all show 20–40% demand spikes. Conversely, January/February are dead zones. The current model has zero temporal awareness.

### Data Source

**Nager.Date** — Free, no API key, no rate limits.
- URL: `https://date.nager.at/api/v3/publicholidays/{year}/{country_code}`
- Returns: date, local name, name, country code, fixed flag, global flag, types

### Architecture

```python
# src/holiday_features.py

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class HolidayFeatureBuilder:
    """Compute holiday proximity features."""

    HOLIDAY_URL = "https://date.nager.at/api/v3/publicholidays/{year}/US"

    # NYC-specific high-demand periods (not federal holidays)
    NYC_DEMAND_PERIODS = {
        "fashion_week_feb": ("02-07", "02-15"),
        "fashion_week_sep": ("09-05", "09-15"),
        "un_week": ("09-20", "09-30"),       # UN General Assembly
        "nyc_marathon": ("11-01", "11-08"),
        "rockefeller_tree": ("11-28", "01-05"),  # Tree lighting to Epiphany
    }

    def __init__(self):
        self.holidays_cache = {}

    def fetch_holidays(self, year: int) -> pd.DataFrame:
        if year in self.holidays_cache:
            return self.holidays_cache[year]

        url = self.HOLIDAY_URL.format(year=year)
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        self.holidays_cache[year] = df
        return df

    def compute_features(self, date_str: str) -> dict:
        """Holiday features for a given date."""
        date = pd.Timestamp(date_str)
        year = date.year

        holidays = self.fetch_holidays(year)

        # Days to next/previous holiday
        future = holidays[holidays["date"] >= date]["date"]
        past = holidays[holidays["date"] <= date]["date"]

        days_to_next = (future.min() - date).days if len(future) > 0 else 999
        days_since_prev = (date - past.max()).days if len(past) > 0 else 999

        # Is within N days of a holiday?
        is_holiday = int(date in holidays["date"].values)
        near_holiday_3 = int(min(days_to_next, days_since_prev) <= 3)
        near_holiday_7 = int(min(days_to_next, days_since_prev) <= 7)

        # NYC demand season
        month = date.month
        is_peak_season = int(month in [6, 7, 8, 11, 12])
        is_low_season = int(month in [1, 2])

        # NYC-specific events
        is_nyc_event = 0
        mm_dd = date.strftime("%m-%d")
        for period_name, (start, end) in self.NYC_DEMAND_PERIODS.items():
            if start <= mm_dd <= end:
                is_nyc_event = 1
                break

        # Weekend bridge (holiday on Tue/Thu → long weekend)
        dow = date.dayofweek
        is_long_weekend = 0
        if days_to_next == 1 and dow in [0, 1, 2]:  # Mon/Tue/Wed before holiday
            is_long_weekend = 1
        if days_since_prev == 1 and dow in [2, 3, 4]:  # Wed/Thu/Fri after holiday
            is_long_weekend = 1

        return {
            "days_to_next_holiday": int(days_to_next),
            "days_since_prev_holiday": int(days_since_prev),
            "is_holiday": is_holiday,
            "near_holiday_3d": near_holiday_3,
            "near_holiday_7d": near_holiday_7,
            "is_peak_season": is_peak_season,
            "is_low_season": is_low_season,
            "is_nyc_event_period": is_nyc_event,
            "is_long_weekend": is_long_weekend,
            "month": month,
            "day_of_week": dow,
            "is_weekend": int(dow >= 5),
        }

    def batch_compute(self, df: pd.DataFrame, date_col: str = "snapshot_date") -> pd.DataFrame:
        """Add holiday features to a DataFrame."""
        features = df[date_col].apply(self.compute_features)
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Integration Note

For the current single-snapshot dataset (2026-06-14), all rows get the same date features. The real power emerges when we have multi-temporal data (Innovation 10). For now, compute features at the **listing level** using `first_review` or `host_since` as a proxy for listing age, and include the static seasonal/month features.

For inference, the API should accept a `target_date` parameter and compute holiday features relative to it.

### Expected Impact

+1–3% R² on current data. **Critical** for any temporal model — without date features, the model cannot distinguish a December prediction from a July one.

---

## Innovation 5: Weather Data (OpenWeatherMap)

### Rationale

Weather affects NYC tourism and therefore STR demand. Rainy weekends reduce occupancy. Heat waves push people to air-conditioned listings. The current model has no weather signal.

### Data Source

**OpenWeatherMap** — Free tier: 1,000 calls/day, historical data available.
- Current: `https://api.openweathermap.org/data/2.5/weather`
- Historical (One Call 3.0): `https://api.openweathermap.org/data/3.0/onecall/timemachine`
- Historical bulk: `https://bulk.openweathermap.org/history/`

### Architecture

```python
# src/weather_features.py

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class WeatherFeatureBuilder:
    """Weather features for NYC STR predictions."""

    NYC_LAT, NYC_LNG = 40.7128, -74.0060

    # Historical monthly averages for NYC (NOAA data, hardcoded fallback)
    NYC_MONTHLY_AVG = {
        1: {"temp": 33, "precip_days": 10, "condition": "cold"},
        2: {"temp": 35, "precip_days": 9, "condition": "cold"},
        3: {"temp": 43, "precip_days": 10, "condition": "cool"},
        4: {"temp": 54, "precip_days": 11, "condition": "mild"},
        5: {"temp": 64, "precip_days": 11, "condition": "warm"},
        6: {"temp": 73, "precip_days": 10, "condition": "hot"},
        7: {"temp": 79, "precip_days": 10, "condition": "hot"},
        8: {"temp": 77, "precip_days": 9, "condition": "hot"},
        9: {"temp": 70, "precip_days": 8, "condition": "warm"},
        10: {"temp": 58, "precip_days": 8, "condition": "mild"},
        11: {"temp": 47, "precip_days": 9, "condition": "cool"},
        12: {"temp": 37, "precip_days": 10, "condition": "cold"},
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def fetch_weather(self, date: str) -> dict:
        """Fetch actual weather for a date (requires One Call 3.0 subscription)."""
        if not self.api_key:
            return None

        dt = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall/timemachine"
            f"?lat={self.NYC_LAT}&lon={self.NYC_LNG}&dt={dt}&appid={self.api_key}&units=imperial"
        )
        resp = requests.get(url)
        if resp.status_code != 200:
            return None

        data = resp.json()
        current = data.get("data", [{}])[0]
        return {
            "temp_f": current.get("temp", 60),
            "feels_like_f": current.get("feels_like", 60),
            "humidity": current.get("humidity", 50),
            "wind_speed": current.get("wind_speed", 5),
            "precipitation": current.get("rain", {}).get("1h", 0) + current.get("snow", {}).get("1h", 0),
            "cloud_cover": current.get("clouds", 50),
            "weather_main": current.get("weather", [{}])[0].get("main", "Clear"),
        }

    def compute_features(self, date: str) -> dict:
        """Weather features — uses API if available, falls back to historical averages."""
        month = pd.Timestamp(date).month
        avg = self.NYC_MONTHLY_AVG[month]

        # Try API first
        api_weather = self.fetch_weather(date) if self.api_key else None

        if api_weather:
            temp = api_weather["temp_f"]
            precip = api_weather["precipitation"]
            cloud = api_weather["cloud_cover"]
            weather_main = api_weather["weather_main"]
        else:
            # Fallback to historical averages with month-level granularity
            temp = avg["temp"]
            precip = avg["precip_days"] / 30.0  # daily probability
            cloud = 50
            weather_main = avg["condition"]

        return {
            "avg_temp_f": temp,
            "avg_temp_c": (temp - 32) * 5 / 9,
            "precip_probability": min(precip, 1.0),
            "cloud_cover_pct": cloud,
            "is_good_weather": int(temp >= 55 and precip < 0.3 and cloud < 50),
            "is_extreme_heat": int(temp >= 90),
            "is_extreme_cold": int(temp <= 25),
            "weather_score": max(0, min(1, (temp - 20) / 60)) * (1 - min(precip, 1)),
        }

    def batch_compute(self, df: pd.DataFrame, date_col: str = "snapshot_date") -> pd.DataFrame:
        features = df[date_col].apply(self.compute_features)
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Expected Impact

+1–2% R². Weather features interact with amenities (`amenity_ac` × `is_extreme_heat` is a strong interaction). The `weather_score` composite feature captures the general "good time to visit NYC" signal.

---

## Innovation 6: Neighborhood Demographics (US Census)

### Rationale

Neighborhood income, education, and population density affect both the type of guests a listing attracts and the price it can command. A listing in a high-income residential neighborhood (Upper East Side) serves a different market than one in a tourist-heavy area (Times Square).

### Data Source

**US Census Bureau API** — Free, no API key required for basic access.
- American Community Survey (ACS) 5-Year Estimates
- URL: `https://data.census.gov/api/access/data`
- Key tables: B19013 (median income), B15003 (education), B01003 (population), B25001 (housing units)
- Tract-level data joins to NYC neighborhoods via FIPS codes

### Architecture

```python
# src/demographic_features.py

import pandas as pd
import numpy as np
import requests
from scipy.spatial import cKDTree

class DemographicFeatureBuilder:
    """US Census demographic features for NYC neighborhoods."""

    CENSUS_BASE = "https://api.census.gov/data"
    YEAR = 2023  # Most recent ACS 5-year

    # NYC county FIPS codes
    NYC_COUNTIES = {
        "Manhattan": "061",
        "Brooklyn": "047",
        "Queens": "081",
        "Bronx": "005",
        "Staten Island": "085",
    }

    # Key ACS variables
    VARIABLES = {
        "B19013_001E": "median_household_income",
        "B15003_022E": "bachelors_degree",
        "B15003_023E": "masters_degree",
        "B15003_025E": "doctorate",
        "B01003_001E": "total_population",
        "B25001_001E": "total_housing_units",
        "B25003_001E": "total_occupied",
        "B25003_002E": "owner_occupied",
        "B25003_003E": "renter_occupied",
        "B08303_001E": "total_commute",
        "B08303_013E": "commute_60_plus",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.tract_data = None
        self.tree = None

    def fetch_census_data(self) -> pd.DataFrame:
        """Fetch ACS 5-year tract-level data for NYC."""
        frames = []
        state_fips = "36"  # New York

        for borough, county_fips in self.NYC_COUNTIES.items():
            variables = ",".join(self.VARIABLES.keys())
            url = (
                f"{self.CENSUS_BASE}/{self.YEAR}/acs/acs5"
                f"?get={variables}"
                f"&for=tract:*"
                f"&in=state:{state_fips}+county:{county_fips}"
            )
            if self.api_key:
                url += f"&key={self.api_key}"

            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()

            # First row is headers
            headers = data[0]
            rows = [dict(zip(headers, row)) for row in data[1:]]
            for row in rows:
                row["borough"] = borough

            frames.extend(rows)

        df = pd.DataFrame(frames)
        # Rename columns
        rename_map = {v: k for k, v in self.VARIABLES.items()}
        df = df.rename(columns=rename_map)

        # Convert to numeric
        for col in self.VARIABLES.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Derived metrics
        df["pct_bachelors_plus"] = (
            (df["bachelors_degree"] + df["masters_degree"] + df["doctorate"])
            / df["total_population"].clip(lower=1) * 100
        )
        df["pct_renter"] = (
            df["renter_occupied"] / df["total_occupied"].clip(lower=1) * 100
        )
        df["housing_density"] = (
            df["total_housing_units"] / df["total_population"].clip(lower=1) * 1000
        )

        self.tract_data = df
        return df

    def load_tract_centroids(self) -> pd.DataFrame:
        """Load tract centroids from Census TIGER/Line shapefiles."""
        # Simplified: use pre-computed centroids or geocode tract boundaries
        # For production, download from:
        # https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_36_tract_500k.zip
        # and compute centroids with geopandas
        raise NotImplementedError("Load tract shapefile and compute centroids")

    def compute_features(self, lat: float, lng: float) -> dict:
        """Look up demographics for the tract containing this point."""
        if self.tract_data is None:
            self.fetch_census_data()

        # Simple nearest-tract lookup using centroids
        # In production, use point-in-polygon with tract geometries
        if self.tree is None:
            self._build_tract_tree()

        point = np.array([lat * 111_000, lng * 85_000])
        _, idx = self.tree.query(point, k=1)
        tract = self.tract_data.iloc[idx]

        return {
            "tract_median_income": tract.get("median_household_income", 60000),
            "tract_pct_college": tract.get("pct_bachelors_plus", 40),
            "tract_pct_renter": tract.get("pct_renter", 65),
            "tract_population": tract.get("total_population", 5000),
            "tract_housing_density": tract.get("housing_density", 500),
            "tract_income_tier": self._income_tier(tract.get("median_household_income", 60000)),
        }

    def _income_tier(self, income: float) -> int:
        if income < 40000:
            return 1  # Low income
        elif income < 70000:
            return 2  # Middle income
        elif income < 120000:
            return 3  # Upper middle
        else:
            return 4  # High income

    def _build_tract_tree(self):
        """Build KD-Tree from tract centroids."""
        coords = self.tract_data[["centroid_lat", "centroid_lng"]].values
        coords_m = np.column_stack([coords[:, 0] * 111_000, coords[:, 1] * 85_000])
        self.tree = cKDTree(coords_m)
```

### Data Preprocessing

```python
# scripts/fetch_demographics.py
"""One-time script: fetch Census data and save as Parquet."""

from src.demographic_features import DemographicFeatureBuilder

builder = DemographicFeatureBuilder()
df = builder.fetch_census_data()
df.to_parquet("data/census/nyc_tract_demographics.parquet", index=False)
print(f"Saved {len(df)} tracts")
```

### Expected Impact

+2–3% R². `tract_median_income` and `tract_pct_college` should correlate with listing price ceiling. `tract_pct_renter` captures neighborhoods where STR competes with long-term rentals (regulatory pressure signal).

---

## Innovation 7: STR Regulation Data (NYC Local Law 18)

### Rationale

NYC Local Law 18 (effective Sep 2023) requires all STR hosts to register with the city. Unregistered listings cannot legally operate. This is the single most impactful regulatory event for NYC STR — it eliminated ~80% of Airbnb listings in NYC. The current model has zero awareness of this.

### Data Source

**NYC Open Data — Short-Term Rental Registrations**
- URL: `https://data.cityofnewyork.us/api/views/...`
- Alternative: Scrape NYC Mayor's Office of Special Enforcement (OSE) registry
- Additional: InsideAirbnb already flags registration status in some scrapes

### Architecture

```python
# src/regulation_features.py

import pandas as pd
import numpy as np

class RegulationFeatureBuilder:
    """NYC STR regulation features."""

    # Local Law 18 key dates
    LL18_ANNOUNCED = "2023-01-01"
    LL18_EFFECTIVE = "2023-09-05"
    LL18_ENFORCEMENT_START = "2024-03-01"

    # Registration status from NYC Open Data
    REGISTRATION_URL = "https://data.cityofnewyork.us/resource/..."

    def __init__(self, registration_data_path: str = None):
        self.registrations = None
        if registration_data_path:
            self.registrations = pd.read_csv(registration_data_path)

    def compute_features(self, listing_id: str, host_id: str, borough: str) -> dict:
        """Regulation features for a listing."""

        # Check registration status
        is_registered = 0
        registration_type = "unknown"

        if self.registrations is not None:
            match = self.registrations[
                self.registrations["airbnb_listing_id"] == listing_id
            ]
            if len(match) > 0:
                is_registered = 1
                registration_type = match.iloc[0].get("registration_type", "whole_apartment")

        # Borough-level regulation stringency
        # Manhattan has strictest enforcement, Staten Island least
        borough_enforcement = {
            "Manhattan": 4,
            "Brooklyn": 3,
            "Queens": 2,
            "Bronx": 1,
            "Staten Island": 1,
        }

        # Whether listing is in a "Class B" multiple dwelling (illegal for STR)
        # Approximation: buildings with 3+ units in residential zones
        # In production, join with DOB buildings dataset
        likely_class_b = 0  # Would need building data

        return {
            "is_registered_str": is_registered,
            "registration_type": registration_type,
            "borough_enforcement_level": borough_enforcement.get(borough, 2),
            "post_ll18": 1,  # Current date is after Sep 2023
            "likely_class_b_building": likely_class_b,
        }

    def compute_risk_score(self, features: dict) -> float:
        """0-1 regulatory risk score. Higher = more risk."""
        score = 0.0

        if not features["is_registered_str"]:
            score += 0.5  # Major risk: unregistered

        score += features["borough_enforcement_level"] * 0.05

        if features["likely_class_b_building"]:
            score += 0.3

        return min(1.0, score)

    def batch_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add regulation features to DataFrame."""
        features = df.apply(
            lambda row: self.compute_features(
                row.get("id", ""),
                row.get("host_id", ""),
                row.get("borough", "Unknown"),
            ),
            axis=1,
        )
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Integration with InsideAirbnb Data

InsideAirbnb scrapes include a `host_total_listings_count` field. Listings where the host has 3+ total listings and is *not* registered are likely professional operators running illegal STRs — the primary target of LL18.

```python
# In engineer_features_v2():
df["likely_professional_host"] = (
    (df["host_listings_count_num"] >= 3) & (df["is_registered_str"] == 0)
).astype(int)
df["regulatory_risk"] = regulation_builder.compute_risk_score_vectorized(df)
```

### Expected Impact

+3–5% R². `is_registered_str` is a binary feature that should have massive predictive power — unregistered listings have near-zero legal revenue. `borough_enforcement_level` captures the geographic gradient of enforcement intensity.

---

## Innovation 8: Review Text Sentiment (NLP)

### Rationale

Guest reviews contain rich signal about listing quality, host behavior, and property conditions that star ratings alone miss. A listing with 100 five-star reviews but text saying "amazing location but the apartment was dirty" has hidden risk. Sentiment analysis extracts this signal.

### Data Source

**InsideAirbnb reviews.csv.gz** — Already downloaded.
- Contains: listing_id, id, date, reviewer_id, reviewer_name, comments
- ~1.5M reviews for NYC

### Architecture

```python
# src/sentiment_features.py

import pandas as pd
import numpy as np
from collections import Counter
import re

class SentimentFeatureBuilder:
    """Extract sentiment and quality signals from review text."""

    # Positive/negative keyword lists (domain-specific for STR reviews)
    POSITIVE_KEYWORDS = {
        "clean", "spotless", "immaculate", "tidy",
        "comfortable", "cozy", "spacious", "modern",
        "amazing", "wonderful", "excellent", "perfect", "fantastic",
        "convenient", "accessible", "central", "walkable",
        "responsive", "helpful", "friendly", "accommodating",
        "quiet", "peaceful", "safe", "secure",
        "well-equipped", "well-appointed", "stocked",
    }

    NEGATIVE_KEYWORDS = {
        "dirty", "filthy", "unclean", "moldy", "dusty",
        "noisy", "loud", "disruptive",
        "broken", "damaged", "malfunctioning", "leak",
        "small", "cramped", "tiny", "claustrophobic",
        "unresponsive", "rude", "unhelpful",
        "unsafe", "sketchy", "dangerous",
        "misleading", "inaccurate", "catfish",
        "bug", "cockroach", "roach", "mouse", "rat", "bedbug",
    }

    # Aspect categories
    ASPECTS = {
        "cleanliness": ["clean", "dirty", "spotless", "filthy", "tidy", "moldy", "dusty", "hygiene"],
        "location": ["location", "neighborhood", "area", "walk", "subway", "train", "bus", "central", "convenient"],
        "communication": ["responsive", "communicat", "repl", "answer", "helpful", "host"],
        "accuracy": ["accurate", "misleading", "photo", "described", "expected", "picture"],
        "value": ["price", "value", "worth", "expensive", "cheap", "affordable", "overpriced"],
        "amenities": ["wifi", "kitchen", "towel", "linen", "shower", "hot water", "heat", "ac", "air conditioning"],
    }

    def __init__(self, reviews_path: str = None):
        self.reviews = None
        if reviews_path:
            self.reviews = pd.read_csv(reviews_path, compression="gzip", low_memory=False)

    def preprocess_text(self, text: str) -> str:
        """Clean review text."""
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r"[^a-z\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def compute_sentiment(self, text: str) -> dict:
        """Compute keyword-based sentiment features for a single review."""
        clean = self.preprocess_text(text)
        words = set(clean.split())

        pos = words & self.POSITIVE_KEYWORDS
        neg = words & self.NEGATIVE_KEYWORDS

        total = len(pos) + len(neg)
        sentiment_score = (len(pos) - len(neg)) / max(total, 1)

        # Aspect presence
        aspect_signals = {}
        for aspect, keywords in self.ASPECTS.items():
            found = [k for k in keywords if k in clean]
            aspect_signals[f"aspect_{aspect}"] = len(found) > 0
            aspect_signals[f"aspect_{aspect}_count"] = len(found)

        return {
            "sentiment_score": sentiment_score,
            "positive_keyword_count": len(pos),
            "negative_keyword_count": len(neg),
            "has_bug_mention": int(bool(words & {"bug", "cockroach", "roach", "mouse", "rat", "bedbug"})),
            "has_cleanliness_complaint": int(bool(words & {"dirty", "filthy", "unclean", "moldy"})),
            "has_noise_complaint": int(bool(words & {"noisy", "loud", "disruptive"})),
            **aspect_signals,
        }

    def compute_listing_features(self, listing_id: int) -> dict:
        """Aggregate sentiment features across all reviews for a listing."""
        if self.reviews is None:
            return self._default_features()

        reviews = self.reviews[self.reviews["listing_id"] == listing_id]
        if len(reviews) == 0:
            return self._default_features()

        sentiments = reviews["comments"].apply(self.compute_sentiment)
        sdf = pd.DataFrame(sentiments.tolist())

        # Aggregate
        features = {
            "review_count_for_sentiment": len(reviews),
            "avg_sentiment": sdf["sentiment_score"].mean(),
            "min_sentiment": sdf["sentiment_score"].min(),
            "sentiment_std": sdf["sentiment_score"].std(),
            "pct_positive_reviews": (sdf["sentiment_score"] > 0.2).mean(),
            "pct_negative_reviews": (sdf["sentiment_score"] < -0.2).mean(),
            "total_bug_mentions": sdf["has_bug_mention"].sum(),
            "total_cleanliness_complaints": sdf["has_cleanliness_complaint"].sum(),
            "total_noise_complaints": sdf["has_noise_complaint"].sum(),
        }

        # Aspect aggregation
        for aspect in self.ASPECTS:
            col = f"aspect_{aspect}"
            if col in sdf.columns:
                features[f"pct_reviews_mention_{aspect}"] = sdf[col].mean()

        return features

    def _default_features(self) -> dict:
        """Default features when no reviews are available."""
        features = {
            "review_count_for_sentiment": 0,
            "avg_sentiment": 0,
            "min_sentiment": 0,
            "sentiment_std": 0,
            "pct_positive_reviews": 0,
            "pct_negative_reviews": 0,
            "total_bug_mentions": 0,
            "total_cleanliness_complaints": 0,
            "total_noise_complaints": 0,
        }
        for aspect in self.ASPECTS:
            features[f"pct_reviews_mention_{aspect}"] = 0
        return features

    def batch_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add sentiment features to a DataFrame."""
        features = df["id"].apply(self.compute_listing_features)
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Batch Processing Pipeline

```python
# scripts/compute_sentiment.py
"""Pre-compute sentiment features for all listings (expensive, run once)."""

import pandas as pd
from src.sentiment_features import SentimentFeatureBuilder

# Load reviews
reviews_path = "data/reviews.csv.gz"
sentiment_builder = SentimentFeatureBuilder(reviews_path)

# Load listings
listings = pd.read_csv("data/listings.csv.gz", low_memory=False)

# Compute sentiment features
result = sentiment_builder.batch_compute(listings)

# Save
sentiment_cols = [c for c in result.columns if c.startswith(("avg_sentiment", "pct_", "total_", "review_count_for"))]
result[["id"] + sentiment_cols].to_parquet("data/listing_sentiment_features.parquet", index=False)
print(f"Computed sentiment for {len(result)} listings")
```

### Expected Impact

+1–2% R². `avg_sentiment` and `pct_negative_reviews` capture quality signals invisible to star ratings. `total_bug_mentions` and `total_cleanliness_complaints` are strong negative predictors.

---

## Innovation 9: Listing Photo Quality Score

### Rationale

Listings with professional, well-lit photos get 2–3x more bookings than those with dark, blurry phone photos. The current model uses `photo_count` as a proxy, but count alone doesn't capture quality.

### Data Source

**Listing photo URLs from InsideAirbnb** — `picture_url` column in listings.csv.gz
- Download and analyze with computer vision

### Architecture

```python
# src/photo_quality.py

import requests
import numpy as np
from PIL import Image
from io import BytesIO
import hashlib

class PhotoQualityScorer:
    """Score listing photo quality using computer vision heuristics."""

    def __init__(self, max_photos: int = 5):
        self.max_photos = max_photos

    def score_listing(self, photo_url: str) -> dict:
        """Score photo quality for a listing from its main photo URL."""
        if not photo_url or not isinstance(photo_url, str):
            return self._default_scores()

        try:
            resp = requests.get(photo_url, timeout=10)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
            return self._score_image(img)
        except Exception:
            return self._default_scores()

    def _score_image(self, img: Image.Image) -> dict:
        """Compute image quality metrics."""
        arr = np.array(img.convert("RGB"), dtype=np.float64)

        # Brightness (mean pixel value, 0-255)
        brightness = arr.mean()

        # Contrast (std of pixel values)
        contrast = arr.std()

        # Saturation (HSV-based)
        # Simplified: use channel diversity as proxy
        channel_means = arr.reshape(-1, 3).mean(axis=0)
        saturation_proxy = channel_means.std()

        # Resolution score (log scale, capped)
        pixels = img.size[0] * img.size[1]
        resolution_score = min(1.0, np.log10(max(pixels, 1)) / 7)  # 10M pixels = 1.0

        # Aspect ratio (professional photos are typically 4:3 or 16:9)
        w, h = img.size
        aspect = w / max(h, 1)
        is_standard_aspect = int(1.2 < aspect < 2.0)

        # Blur detection (Laplacian variance proxy)
        # Simplified: use edge detection via gradient magnitude
        gray = arr.mean(axis=2)
        gy = np.abs(np.diff(gray, axis=0))
        gx = np.abs(np.diff(gray, axis=1))
        sharpness = (gx.mean() + gy.mean()) / 2

        # Composite score (0-1)
        quality_score = (
            self._normalize(brightness, 40, 180) * 0.2 +  # Not too dark/bright
            self._normalize(contrast, 20, 80) * 0.2 +      # Good contrast
            self._normalize(sharpness, 2, 30) * 0.3 +      # Sharp
            resolution_score * 0.2 +                         # High res
            is_standard_aspect * 0.1                          # Good framing
        )

        return {
            "photo_brightness": float(brightness),
            "photo_contrast": float(contrast),
            "photo_sharpness": float(sharpness),
            "photo_resolution_score": float(resolution_score),
            "photo_quality_score": float(np.clip(quality_score, 0, 1)),
            "photo_is_standard_aspect": is_standard_aspect,
        }

    def _normalize(self, value: float, low: float, high: float) -> float:
        """Normalize to 0-1 with clamping."""
        return float(np.clip((value - low) / (high - low), 0, 1))

    def _default_scores(self) -> dict:
        return {
            "photo_brightness": 100,
            "photo_contrast": 40,
            "photo_sharpness": 10,
            "photo_resolution_score": 0.5,
            "photo_quality_score": 0.5,
            "photo_is_standard_aspect": 1,
        }

    def batch_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score all listings. WARNING: slow (downloads images)."""
        features = df["picture_url"].apply(self.score_listing)
        feature_df = pd.DataFrame(features.tolist(), index=df.index)
        return pd.concat([df, feature_df], axis=1)
```

### Scalable Alternative: Pre-trained Model

For production, use a pre-trained image quality assessment model instead of heuristics:

```python
# Using pyiqa (pip install pyiqa)
import pyiqa

def score_with_model(img_path: str) -> float:
    """Use MUSIQ (multi-scale image quality transformer) to score."""
    model = pyiqa.create_metric("musiq", device="cpu")
    score = model(img_path)
    return float(score)
```

### Expected Impact

+1–2% R². `photo_quality_score` captures the listing presentation quality that drives booking conversion. This feature also has practical value — hosts can be advised to improve photos if their score is low.

---

## Innovation 10: Cross-City Data Architecture

### Rationale

The current model is NYC-only with borough one-hot encoding. Scaling to other cities (LA, Miami, London) requires a fundamentally different architecture — one that learns city-agnostic patterns while respecting city-specific dynamics.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CROSS-CITY DATA PLATFORM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   NYC    │  │    LA    │  │  Miami   │  │  London  │       │
│  │ Pipeline │  │ Pipeline │  │ Pipeline │  │ Pipeline │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
│       ▼              ▼              ▼              ▼             │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              UNIFIED SCHEMA (Bronze Layer)            │       │
│  │  listing_id | city | lat | lng | price | bedrooms    │       │
│  │  | accommodates | amenities | host_id | ...          │       │
│  └──────────────────────┬───────────────────────────────┘       │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           FEATURE STORE (Silver Layer)                │       │
│  │                                                      │       │
│  │  City-Universal Features:                            │       │
│  │    - price_per_person, beds_per_person                │       │
│  │    - dist_to_transit_km, transit_density              │       │
│  │    - neighborhood_income_pct, pct_college             │       │
│  │    - photo_quality_score, avg_sentiment               │       │
│  │    - host_experience_months, host_response_rate       │       │
│  │    - num_amenities, amenity_flags                     │       │
│  │                                                      │       │
│  │  City-Specific Features (learned embeddings):         │       │
│  │    - city_embedding (learned 8-dim vector)            │       │
│  │    - neighborhood_embedding (learned 16-dim)          │       │
│  │    - local_regulation_score                           │       │
│  │    - local_seasonality_index                          │       │
│  └──────────────────────┬───────────────────────────────┘       │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            MODEL LAYER (Gold Layer)                   │       │
│  │                                                      │       │
│  │  Option A: City-specific XGBoost models               │       │
│  │    - One model per city                               │       │
│  │    - Same feature schema, different weights            │       │
│  │    - Simplest, best for < 10 cities                   │       │
│  │                                                      │       │
│  │  Option B: Multi-task neural network                  │       │
│  │    - Shared trunk + city-specific heads               │       │
│  │    - Learns cross-city patterns                       │       │
│  │    - Best for 10+ cities                              │       │
│  │                                                      │       │
│  │  Option C: Meta-learning (MAML)                       │       │
│  │    - Train on many cities, fine-tune on new city      │       │
│  │    - Best for rapid expansion to new markets          │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Unified Schema

```python
# src/cross_city/schema.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class UnifiedListing:
    """City-agnostic listing schema. Every city pipeline maps to this."""

    # Identity
    listing_id: str
    city: str
    country: str

    # Location
    latitude: float
    longitude: float
    neighborhood: str
    borough_district: Optional[str]  # NYC borough, LA region, etc.

    # Listing attributes
    property_type: str      # Entire home, Private room, etc.
    room_type: str          # Entire home/apt, Private room, Shared room
    accommodates: int
    bedrooms: float
    bathrooms: float
    beds: float
    minimum_nights: int
    nightly_rate_usd: float  # Normalized to USD

    # Host attributes
    host_id: str
    host_is_superhost: bool
    host_listings_count: int
    host_response_rate: float
    host_acceptance_rate: float
    host_response_time: str
    host_experience_months: int

    # Quality signals
    num_amenities: int
    amenity_flags: dict     # {wifi: 1, kitchen: 1, ...}
    photo_count: int
    photo_quality_score: float
    description_length: int

    # Regulation
    is_registered: bool
    local_regulation_score: float  # 0=none, 1=strict

    # Transit
    dist_to_transit_km: float
    transit_density_1km: int

    # Demographics
    neighborhood_median_income: float
    neighborhood_pct_college: float

    # Reviews (for training only — NOT used as features for prediction)
    review_count: int
    avg_review_score: float
    avg_sentiment: float

    # Target
    estimated_annual_revenue_usd: float


class CityPipeline:
    """Base class for city-specific data pipelines."""

    CITY_NAME: str = ""
    CURRENCY: str = "USD"
    TRANSIT_SOURCE: str = ""

    def load_raw(self) -> pd.DataFrame:
        raise NotImplementedError

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    def map_to_unified(self, df: pd.DataFrame) -> list[UnifiedListing]:
        raise NotImplementedError

    def run(self) -> pd.DataFrame:
        raw = self.load_raw()
        cleaned = self.clean(raw)
        unified = self.map_to_unified(cleaned)
        return pd.DataFrame([u.__dict__ for u in unified])


class NYCPipeline(CityPipeline):
    CITY_NAME = "new_york"
    CURRENCY = "USD"

    def load_raw(self):
        return pd.read_csv("data/insideairbnb/nyc/listings.csv.gz", low_memory=False)

    def clean(self, df):
        # Existing filter_listings logic
        ...

    def map_to_unified(self, df):
        listings = []
        for _, row in df.iterrows():
            listings.append(UnifiedListing(
                listing_id=str(row["id"]),
                city="new_york",
                country="US",
                latitude=row["latitude"],
                longitude=row["longitude"],
                neighborhood=row.get("neighbourhood", ""),
                borough_district=row.get("neighbourhood_group_cleansed", ""),
                property_type=row.get("property_type", "Unknown"),
                room_type=row.get("room_type", "Entire home/apt"),
                accommodates=int(row.get("accommodates", 2)),
                ...
            ))
        return listings
```

### Multi-City Model Training

```python
# src/cross_city/model.py

import xgboost as xgb
import numpy as np

class CrossCityModel:
    """Two-stage model: city-agnostic features + city-specific fine-tuning."""

    def __init__(self):
        self.global_model = None
        self.city_models = {}

    def train_global(self, X: np.ndarray, y: np.ndarray):
        """Train on all cities combined."""
        self.global_model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
        )
        self.global_model.fit(X, y)

    def train_city(self, city: str, X: np.ndarray, y: np.ndarray):
        """Fine-tune global model for a specific city."""
        city_model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.01,
        )
        # Initialize with global model predictions as base
        city_model.fit(X, y, xgb_model=self.global_model)
        self.city_models[city] = city_model

    def predict(self, city: str, X: np.ndarray) -> np.ndarray:
        if city in self.city_models:
            return self.city_models[city].predict(X)
        return self.global_model.predict(X)
```

### Data Lake Structure

```
data/
├── raw/
│   ├── new_york/
│   │   ├── listings.csv.gz
│   │   ├── reviews.csv.gz
│   │   └── calendar.csv.gz
│   ├── los_angeles/
│   │   ├── listings.csv.gz
│   │   └── ...
│   ├── miami/
│   └── london/
├── processed/
│   ├── new_york/
│   │   ├── listings_unified.parquet
│   │   ├── transit_features.parquet
│   │   ├── sentiment_features.parquet
│   │   └── demographic_features.parquet
│   ├── los_angeles/
│   └── ...
├── features/
│   ├── feature_store.parquet      # All cities, unified schema
│   └── feature_metadata.json
├── models/
│   ├── global_v1.json
│   ├── new_york_v1.json
│   └── ...
└── events/
    ├── nyc_events_2026-06.parquet
    └── ...
```

### City Expansion Checklist

```python
# scripts/add_city.py
"""Template for adding a new city to the platform."""

CHECKLIST = """
1. Download InsideAirbnb data for {city}
2. Create city pipeline class inheriting CityPipeline
3. Implement load_raw(), clean(), map_to_unified()
4. Run transit feature builder with local transit data
5. Fetch Census/local demographics data
6. Fetch local STR regulations
7. Run sentiment analysis on reviews
8. Run photo quality scoring
9. Compute holiday features for local holidays
10. Train city-specific model (fine-tune from global)
11. Validate: MAPE < 30%, R² > 0.5
12. Deploy city-specific API endpoint
"""
```

### Expected Impact

This architecture enables:
- **Rapid city expansion**: New city = ~2 days of work (data download + pipeline + training)
- **Cross-city transfer learning**: A model trained on NYC+LA+Miami learns generalizable STR patterns
- **Consistent feature schema**: All cities produce identical feature vectors
- **A/B testing**: Compare city-specific model vs. global model per city

---

## Implementation Priority

| Priority | Innovation | Effort | Impact | Dependencies |
|----------|-----------|--------|--------|--------------|
| 🔴 P0 | #1 Remove leaky features | 1 day | Critical | None |
| 🔴 P0 | #7 STR regulation data | 1 day | High | NYC Open Data |
| 🟡 P1 | #2 Subway/transit distance | 1 day | High | MTA data |
| 🟡 P1 | #4 Holiday data | 0.5 day | Medium | Nager.Date API |
| 🟡 P1 | #6 Neighborhood demographics | 2 days | Medium | Census API |
| 🟡 P1 | #8 Review sentiment | 2 days | Medium | Reviews.csv.gz |
| 🟢 P2 | #3 Event data | 2 days | Medium | Ticketmaster API key |
| 🟢 P2 | #5 Weather data | 1 day | Low-Medium | OpenWeatherMap key |
| 🟢 P2 | #9 Photo quality | 2 days | Low-Medium | Photo URLs |
| 🔵 P3 | #10 Cross-city architecture | 5 days | Strategic | All above |

### Sprint Plan

**Sprint 1 (Week 1): Fix the Foundation**
- Remove leaky features (#1)
- Add regulation data (#7)
- Add transit features (#2)
- Add holiday features (#4)
- Retrain model → expect R² ~0.45–0.55

**Sprint 2 (Week 2): Enrich Features**
- Add demographics (#6)
- Add sentiment (#8)
- Add weather (#5)
- Retrain model → expect R² ~0.55–0.65

**Sprint 3 (Week 3): Polish & Expand**
- Add events (#3)
- Add photo quality (#9)
- Final model → expect R² ~0.60–0.70
- Begin cross-city architecture (#10)

**Sprint 4 (Week 4): Architecture**
- Build unified schema
- Add second city (LA or Miami)
- Cross-city model training
- Production deployment

---

## Expected Final Model Performance

| Metric | Current (Leaky) | After Sprint 1 | After Sprint 2 | After Sprint 3 |
|--------|-----------------|-----------------|-----------------|-----------------|
| R² | 0.997 (fake) | 0.45–0.55 | 0.55–0.65 | 0.60–0.70 |
| MAPE | 2.0% (fake) | 25–35% | 20–30% | 18–25% |
| MdAPE | 0.8% (fake) | 15–20% | 12–18% | 10–15% |

These are **honest** numbers. A model that predicts STR revenue within 15–20% (median) is genuinely useful for hosts making pricing decisions.

---

## Data Sources Summary

| Source | URL | Cost | Rate Limit | Update Freq |
|--------|-----|------|------------|-------------|
| InsideAirbnb | insideairbnb.com | Free (CC BY 4.0) | None | Quarterly |
| MTA GTFS | mta.info | Free | None | Daily |
| NYC Open Data | data.cityofnewyork.us | Free | None | Monthly |
| Nager.Date | date.nager.at | Free | None | Annual |
| Ticketmaster | developer.ticketmaster.com | Free | 5K/day | Real-time |
| US Census ACS | api.census.gov | Free | 500/key/day | Annual |
| OpenWeatherMap | openweathermap.org | Free | 1K/day | Hourly |
| OSM/Nominatim | nominatim.openstreetmap.org | Free | 1/sec | Weekly |
