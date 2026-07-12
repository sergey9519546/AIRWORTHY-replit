#!/usr/bin/env python3
"""
Phase 1b: Add enhanced features (transit, host response, amenities).
Run AFTER prepare_data.py. Modifies train.csv and test.csv in place.
"""

import pandas as pd
import numpy as np
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.transit_features import TransitFeatureBuilder

TRAIN_PATH = os.path.join(BASE_DIR, "data", "train.csv")
TEST_PATH = os.path.join(BASE_DIR, "data", "test.csv")
FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")


def add_transit_features(df):
    """Add subway proximity features."""
    print("  Adding transit features...")
    builder = TransitFeatureBuilder()
    features_list = []
    for _, row in df.iterrows():
        feat = builder.compute_features(row["latitude"], row["longitude"])
        features_list.append(feat)
    feat_df = pd.DataFrame(features_list, index=df.index)
    return pd.concat([df, feat_df], axis=1)


def add_enhanced_features(df):
    """Add host response, amenities, and quality proxy features."""
    print("  Adding enhanced features...")

    # Host response rate (0-1) — NaN in data, use default
    if "host_response_rate" in df.columns and df["host_response_rate"].notna().any():
        df["host_response_rate_num"] = (
            pd.to_numeric(df["host_response_rate"], errors="coerce").fillna(80) / 100.0
        )
    else:
        df["host_response_rate_num"] = 0.8

    # Host acceptance rate (0-1) — NaN in data, use default
    if "host_acceptance_rate" in df.columns and df["host_acceptance_rate"].notna().any():
        df["host_acceptance_rate_num"] = (
            pd.to_numeric(df["host_acceptance_rate"], errors="coerce").fillna(80) / 100.0
        )
    else:
        df["host_acceptance_rate_num"] = 0.8

    # Host response time (1=fast, 4=slow) — NaN in data, use default
    if "host_response_time" in df.columns and df["host_response_time"].notna().any():
        hrt = df["host_response_time"]
        if hrt.dtype == object:  # string
            time_map = {"within an hour": 1, "within a few hours": 2, "within a day": 3, "a few days or more": 4}
            df["host_response_time_num"] = hrt.str.lower().map(time_map).fillna(3)
        else:  # already numeric or NaN
            df["host_response_time_num"] = pd.to_numeric(hrt, errors="coerce").fillna(3)
    else:
        df["host_response_time_num"] = 3

    # Number of amenities
    if "amenities" in df.columns:
        df["num_amenities"] = df["amenities"].fillna("[]").str.count(",") + 1
    else:
        df["num_amenities"] = 10

    # Amenity flags
    if "amenities" in df.columns:
        amenities_lower = df["amenities"].fillna("[]").str.lower()
        for amenity, pattern in [
            ("wifi", "wifi"), ("kitchen", "kitchen"), ("washer", "washer"),
            ("dryer", "dryer"), ("ac", "air conditioning"), ("heating", "heating"),
            ("tv", '"tv"'), ("elevator", "elevator"), ("gym", "gym"),
            ("pool", "pool"), ("balcony", "balcony"), ("parking", "parking"),
        ]:
            df[f"amenity_{amenity}"] = amenities_lower.str.contains(pattern, na=False).astype(int)
    else:
        for amenity in ["wifi", "kitchen", "washer", "dryer", "ac", "heating", "tv", "elevator", "gym", "pool", "balcony", "parking"]:
            df[f"amenity_{amenity}"] = 0

    # Derived ratios
    df["beds_per_person"] = df["beds_num"] / df["accommodates_num"].clip(lower=1)
    df["bath_to_bed_ratio"] = df["bathrooms_num"] / df["bedrooms_num"].clip(lower=1)

    return df


def main():
    print("=" * 60)
    print("PHASE 1b: ENHANCED FEATURES")
    print("=" * 60)

    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)
    print(f"  Train: {len(train):,}, Test: {len(test):,}")

    # Add enhanced features
    train = add_enhanced_features(train)
    test = add_enhanced_features(test)

    # Add transit features
    train = add_transit_features(train)
    test = add_transit_features(test)

    # Update feature list
    with open(FEATURES_PATH) as f:
        meta = json.load(f)

    new_features = [
        "host_response_rate_num", "host_acceptance_rate_num", "host_response_time_num",
        "num_amenities",
        "amenity_wifi", "amenity_kitchen", "amenity_washer", "amenity_dryer",
        "amenity_ac", "amenity_heating", "amenity_tv", "amenity_elevator",
        "amenity_gym", "amenity_pool", "amenity_balcony", "amenity_parking",
        "beds_per_person", "bath_to_bed_ratio",
        "dist_to_subway_km", "subway_within_200m", "subway_within_400m", "transit_density_1km",
    ]

    # Add new features to existing list (avoid duplicates)
    existing = set(meta["features"])
    for f in new_features:
        if f not in existing:
            meta["features"].append(f)

    print(f"\n  Total features: {len(meta['features'])}")

    # Save
    train.to_csv(TRAIN_PATH, index=False)
    test.to_csv(TEST_PATH, index=False)
    with open(FEATURES_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Enhanced features added!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
