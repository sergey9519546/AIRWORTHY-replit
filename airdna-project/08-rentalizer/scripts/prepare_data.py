#!/usr/bin/env python3
"""
Phase 1: Data Preparation — FIXED VERSION
- STR only (min_nights < 30)
- Non-leaky features only
- Proper train/test split
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SOURCE = os.path.join(BASE_DIR, "..", "06-insideairbnb-data", "listings.csv.gz")
TRAIN_PATH = os.path.join(BASE_DIR, "data", "train.csv")
TEST_PATH = os.path.join(BASE_DIR, "data", "test.csv")
FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")


def load_and_filter():
    """Load and filter to STR entire homes with revenue."""
    df = pd.read_csv(DATA_SOURCE, low_memory=False)
    n = len(df)

    # Entire home only
    df = df[df["room_type"] == "Entire home/apt"].copy()
    print(f"  Entire home: {len(df):,} (dropped {n - len(df):,})")
    n = len(df)

    # Has availability
    df = df[df["has_availability"] == "t"].copy()
    print(f"  Available: {len(df):,} (dropped {n - len(df):,})")
    n = len(df)

    # STRICT: Short-term only (min_nights < 30)
    df["minimum_nights_num"] = pd.to_numeric(df["minimum_nights"], errors="coerce")
    df = df[df["minimum_nights_num"] < 30].copy()
    print(f"  STR only (min<30): {len(df):,} (dropped {n - len(df):,})")
    n = len(df)

    # Has revenue
    df["revenue"] = pd.to_numeric(df.get("estimated_revenue_l365d", pd.Series(dtype=float)), errors="coerce")
    df = df.dropna(subset=["revenue"])
    df = df[df["revenue"] > 0].copy()
    print(f"  Has revenue>0: {len(df):,} (dropped {n - len(df):,})")
    n = len(df)

    # Valid price
    df["price_num"] = pd.to_numeric(
        df["price"].astype(str).str.replace("$", "").str.replace(",", ""), errors="coerce"
    )
    df = df[df["price_num"] > 0].copy()
    print(f"  Valid price: {len(df):,} (dropped {n - len(df):,})")

    # Outliers
    p1, p99 = df["revenue"].quantile(0.01), df["revenue"].quantile(0.99)
    df = df[(df["revenue"] >= p1) & (df["revenue"] <= p99)].copy()
    print(f"  After outliers: {len(df):,}")

    return df


def engineer_features(df):
    """Create NON-LEAKY features only."""
    # Numeric
    df["accommodates_num"] = pd.to_numeric(df["accommodates"], errors="coerce").fillna(2)
    df["bedrooms_num"] = pd.to_numeric(df["bedrooms"], errors="coerce").fillna(0)
    df["bathrooms_num"] = pd.to_numeric(df.get("bathrooms"), errors="coerce").fillna(1)
    df["beds_num"] = pd.to_numeric(df.get("beds"), errors="coerce").fillna(df["accommodates_num"] / 2)
    df["host_listings_count_num"] = pd.to_numeric(df.get("host_listings_count"), errors="coerce").fillna(1)

    # Host attributes
    df["superhost_num"] = (df.get("host_is_superhost", pd.Series(dtype=str)) == "t").astype(int)
    df["instant_bookable_num"] = (df.get("instant_bookable", pd.Series(dtype=str)) == "t").astype(int)

    # Host experience
    df["host_experience_months"] = compute_months_since(df, "host_since")

    # Amenities
    amenities_col = df.get("amenities", pd.Series(dtype=str)).fillna("[]").str.lower()
    for amenity, pattern in [
        ("wifi", "wifi"), ("kitchen", "kitchen"), ("washer", "washer"),
        ("dryer", "dryer"), ("ac", "air conditioning"), ("heating", "heating"),
        ("tv", '"tv"'), ("elevator", "elevator"), ("gym", "gym"),
        ("pool", "pool"), ("balcony", "balcony"), ("parking", "parking"),
    ]:
        df[f"amenity_{amenity}"] = amenities_col.str.contains(pattern, na=False).astype(int)

    # Derived
    df["price_per_person"] = df["price_num"] / df["accommodates_num"].clip(lower=1)
    df["beds_per_person"] = df["beds_num"] / df["accommodates_num"].clip(lower=1)
    df["bath_to_bed_ratio"] = df["bathrooms_num"] / df["bedrooms_num"].clip(lower=1)
    df["num_amenities"] = amenities_col.str.count(",") + 1

    # Borough
    borough_col = "neighbourhood_group_cleansed"
    df["borough"] = df[borough_col].fillna("Unknown") if borough_col in df.columns else "Unknown"

    # Property type
    if "property_type" in df.columns:
        prop_counts = df["property_type"].value_counts()
        rare = prop_counts[prop_counts < 10].index
        df["property_type_clean"] = df["property_type"].replace(rare, "Other")
    else:
        df["property_type_clean"] = "Unknown"

    # Target
    df["log_revenue"] = np.log1p(df["revenue"])

    # PII removal
    for col in ["host_name", "host_location", "host_about", "name", "description"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    return df


def compute_months_since(df, col):
    if col not in df.columns:
        return pd.Series(36, index=df.index)
    dates = pd.to_datetime(df[col], errors="coerce")
    ref = pd.Timestamp("2026-06-14")
    return ((ref - dates).dt.days / 30.44).round().fillna(36)


def one_hot_encode(df):
    borough_dummies = pd.get_dummies(df["borough"], prefix="borough", dtype=int)
    df = pd.concat([df, borough_dummies], axis=1)
    prop_dummies = pd.get_dummies(df["property_type_clean"], prefix="prop", dtype=int)
    df = pd.concat([df, prop_dummies], axis=1)
    return df


def get_feature_columns():
    """NON-LEAKY features only. No reviews, no availability, no review_score."""
    return [
        "price_num", "accommodates_num", "bedrooms_num", "bathrooms_num",
        "beds_num", "minimum_nights_num", "host_listings_count_num",
        "latitude", "longitude",
        "superhost_num", "instant_bookable_num", "host_experience_months",
        "amenity_wifi", "amenity_kitchen", "amenity_washer", "amenity_dryer",
        "amenity_ac", "amenity_heating", "amenity_tv", "amenity_elevator",
        "amenity_gym", "amenity_pool", "amenity_balcony", "amenity_parking",
        "price_per_person", "beds_per_person", "bath_to_bed_ratio", "num_amenities",
    ]


def main():
    print("=" * 60)
    print("PHASE 1: DATA PREPARATION (FIXED — STR ONLY)")
    print("=" * 60)

    df = load_and_filter()
    print(f"\nEngineering features...")
    df = engineer_features(df)
    df = one_hot_encode(df)

    features = get_feature_columns()
    borough_cols = [c for c in df.columns if c.startswith("borough_")]
    prop_cols = [c for c in df.columns if c.startswith("prop_")]
    all_features = features + borough_cols + prop_cols

    # Fill NaN
    df[all_features] = df[all_features].fillna(0)

    # Split
    df["revenue_tier"] = pd.qcut(df["revenue"], 3, labels=False, duplicates="drop")
    df["strat_key"] = df["borough"].astype(str) + "_" + df["revenue_tier"].astype(str)
    strat_counts = df["strat_key"].value_counts()
    valid_strats = strat_counts[strat_counts >= 2].index
    df_valid = df[df["strat_key"].isin(valid_strats)].copy()

    train, test = train_test_split(df_valid, test_size=0.2, stratify=df_valid["strat_key"], random_state=42)

    print(f"\n  Train: {len(train):,}")
    print(f"  Test:  {len(test):,}")
    print(f"  Features: {len(all_features)}")
    print(f"\n  Revenue (train): median=${train['revenue'].median():,.0f}, mean=${train['revenue'].mean():,.0f}")

    # Save
    os.makedirs(os.path.dirname(TRAIN_PATH), exist_ok=True)
    train.to_csv(TRAIN_PATH, index=False)
    test.to_csv(TEST_PATH, index=False)

    meta = {"features": all_features, "n_train": len(train), "n_test": len(test), "created_at": datetime.now().isoformat()}
    os.makedirs(os.path.dirname(FEATURES_PATH), exist_ok=True)
    with open(FEATURES_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Data preparation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
