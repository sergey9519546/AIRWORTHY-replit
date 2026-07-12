"""Feature engineering for inference."""
import json
import os
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from .comp_finder import Comp

# Load NYC borough boundaries once at module level
_GEOJSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nyc-boroughs.geojson")
_borough_shapes = []
try:
    with open(_GEOJSON_PATH) as f:
        _geojson = json.load(f)
    for feature in _geojson["features"]:
        _borough_shapes.append({
            "name": feature["properties"].get("BoroName", feature["properties"].get("boro_name", "Unknown")),
            "shape": shape(feature["geometry"]),
        })
except Exception:
    _borough_shapes = []


def build_features(
    nightly_rate: float,
    bedrooms: int,
    bathrooms: int,
    accommodates: int,
    lat: float,
    lng: float,
    comps: list[Comp],
    borough: str,
    feature_columns: list[str],
    minimum_nights: int = 1,
    is_superhost: bool = False,
    host_listings_count: int = 1,
) -> dict:
    """Build feature vector for a single prediction."""
    features = {}

    # User input
    features["price_num"] = nightly_rate
    features["accommodates_num"] = accommodates
    features["bedrooms_num"] = bedrooms
    features["bathrooms_num"] = bathrooms
    features["beds_num"] = max(1, accommodates // 2)
    features["minimum_nights_num"] = minimum_nights
    features["latitude"] = lat
    features["longitude"] = lng

    # Host attributes (from user input, not hardcoded)
    features["host_listings_count_num"] = host_listings_count
    features["superhost_num"] = int(is_superhost)
    features["instant_bookable_num"] = 0

    # Derived
    features["price_per_person"] = nightly_rate / max(accommodates, 1)
    features["beds_per_person"] = (max(1, accommodates // 2)) / max(accommodates, 1)
    features["bath_to_bed_ratio"] = bathrooms / max(bedrooms, 1)
    features["num_amenities"] = 10  # Default

    # Borough one-hot encoding
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    for b in boroughs:
        features[f"borough_{b}"] = 1 if borough == b else 0

    # Property type one-hot (default to "Entire rental unit")
    prop_types = ['prop_Entire condo', 'prop_Entire guest suite', 'prop_Entire home', 'prop_Entire loft', 'prop_Entire rental unit', 'prop_Entire serviced apartment', 'prop_Entire townhouse', 'prop_Other', 'prop_Room in aparthotel']
    for pt in prop_types:
        features[f"prop_{pt}"] = 1 if pt == "Entire rental unit" else 0

    # Build feature vector in correct order
    vector = {}
    for col in feature_columns:
        vector[col] = features.get(col, 0)

    return vector


def get_borough_from_coords(lat: float, lng: float) -> str:
    """Determine borough from coordinates using GeoJSON polygon lookup."""
    if _borough_shapes:
        point = Point(lng, lat)  # GeoJSON is (lng, lat)
        for entry in _borough_shapes:
            if entry["shape"].contains(point):
                return entry["name"]
    # Fallback: improved bounding box approach
    # Staten Island: south of 40.65, west of -74.05
    if lat < 40.65 and lng < -74.05:
        return "Staten Island"
    # Bronx: north of 40.79
    if lat > 40.79:
        return "Bronx"
    # Queens: east of -73.82
    if lng > -73.82:
        return "Queens"
    # Brooklyn: south of 40.68, east of -73.95
    if lat < 40.68 and lng > -73.95:
        return "Brooklyn"
    # Manhattan: everything else within NYC bounds
    return "Manhattan"
