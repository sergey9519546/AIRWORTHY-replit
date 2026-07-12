#!/usr/bin/env python3
"""
Phase 1c: Add holiday, demographic, and regulation features.
Run AFTER add_enhanced_features.py. Modifies train.csv and test.csv in place.
"""

import pandas as pd
import numpy as np
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_PATH = os.path.join(BASE_DIR, "data", "train.csv")
TEST_PATH = os.path.join(BASE_DIR, "data", "test.csv")
FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")
HOLIDAYS_PATH = os.path.join(BASE_DIR, "data", "holidays_2026.json")


def add_holiday_features(df):
    """Add holiday proximity features."""
    print("  Adding holiday features...")

    # Load holidays
    with open(HOLIDAYS_PATH) as f:
        holidays = json.load(f)

    holiday_dates = [pd.Timestamp(h["date"]) for h in holidays]
    ref = pd.Timestamp("2026-06-14")

    # Days to next holiday
    future_holidays = [d for d in holiday_dates if d > ref]
    if future_holidays:
        days_to_next = min((d - ref).days for d in future_holidays)
    else:
        days_to_next = 180

    # Days since last holiday
    past_holidays = [d for d in holiday_dates if d <= ref]
    if past_holidays:
        days_since_last = min((ref - d).days for d in past_holidays)
    else:
        days_since_last = 180

    # Count holidays in next 30/60/90 days
    holidays_30 = sum(1 for d in future_holidays if (d - ref).days <= 30)
    holidays_60 = sum(1 for d in future_holidays if (d - ref).days <= 60)
    holidays_90 = sum(1 for d in future_holidays if (d - ref).days <= 90)

    # NYC-specific high-demand periods (approximate dates)
    nyc_peak = [
        ("2026-02-14", "Valentine's Day"),
        ("2026-05-25", "Memorial Day"),
        ("2026-07-04", "Independence Day"),
        ("2026-09-07", "Labor Day"),
        ("2026-11-26", "Thanksgiving"),
        ("2026-12-25", "Christmas"),
        ("2026-12-31", "New Year's Eve"),
        ("2026-09-14", "Fashion Week"),
        ("2026-11-01", "NYC Marathon"),
    ]

    nyc_peak_dates = [pd.Timestamp(d) for d, _ in nyc_peak]
    future_peaks = [d for d in nyc_peak_dates if d > ref]
    days_to_peak = min((d - ref).days for d in future_peaks) if future_peaks else 180

    # Apply same values to all rows (same point in time)
    df["days_to_next_holiday"] = days_to_next
    df["days_since_last_holiday"] = days_since_last
    df["holidays_next_30d"] = holidays_30
    df["holidays_next_60d"] = holidays_60
    df["holidays_next_90d"] = holidays_90
    df["days_to_nyc_peak"] = days_to_peak
    df["is_summer"] = int(ref.month in [6, 7, 8])
    df["is_holiday_season"] = int(ref.month in [11, 12])

    return df


def add_demographic_features(df):
    """Add neighborhood demographic features from Census data."""
    print("  Adding demographic features...")

    # NYC borough-level median income and demographics (2023 ACS estimates)
    borough_demographics = {
        "Manhattan": {"median_income": 93651, "college_pct": 0.64, "renter_pct": 0.76, "pop_density": 27751},
        "Brooklyn": {"median_income": 65351, "college_pct": 0.40, "renter_pct": 0.70, "pop_density": 36147},
        "Queens": {"median_income": 75886, "college_pct": 0.36, "renter_pct": 0.56, "pop_density": 21460},
        "Bronx": {"median_income": 40018, "college_pct": 0.22, "renter_pct": 0.80, "pop_density": 33811},
        "Staten Island": {"median_income": 82373, "college_pct": 0.34, "renter_pct": 0.31, "pop_density": 8112},
    }

    # Get borough from one-hot columns
    def get_borough(row):
        for col in ["borough_Manhattan", "borough_Brooklyn", "borough_Queens", "borough_Bronx", "borough_Staten Island"]:
            if row.get(col, 0) == 1:
                return col.replace("borough_", "")
        return "Manhattan"

    df["_borough_label"] = df.apply(get_borough, axis=1)

    for metric in ["median_income", "college_pct", "renter_pct", "pop_density"]:
        df[f"borough_{metric}"] = df["_borough_label"].map(
            {k: v[metric] for k, v in borough_demographics.items()}
        ).fillna(0)

    df = df.drop(columns=["_borough_label"])
    return df


def add_regulation_features(df):
    """Add NYC STR regulation features (Local Law 18)."""
    print("  Adding regulation features...")

    # NYC Local Law 18 (effective Sep 2023): hosts must register with city
    # Impact: unregistered listings can't operate, reduces supply
    # Approximate registration rates by borough (from public reports)
    reg_data = {
        "Manhattan": {"registration_rate": 0.35, "enforcement_level": 3, "legal_risk": 0.7},
        "Brooklyn": {"registration_rate": 0.25, "enforcement_level": 2, "legal_risk": 0.5},
        "Queens": {"registration_rate": 0.20, "enforcement_level": 2, "legal_risk": 0.4},
        "Bronx": {"registration_rate": 0.15, "enforcement_level": 1, "legal_risk": 0.3},
        "Staten Island": {"registration_rate": 0.10, "enforcement_level": 1, "legal_risk": 0.2},
    }

    def get_borough(row):
        for col in ["borough_Manhattan", "borough_Brooklyn", "borough_Queens", "borough_Bronx", "borough_Staten Island"]:
            if row.get(col, 0) == 1:
                return col.replace("borough_", "")
        return "Manhattan"

    df["_borough_label"] = df.apply(get_borough, axis=1)

    for metric in ["registration_rate", "enforcement_level", "legal_risk"]:
        df[f"ll18_{metric}"] = df["_borough_label"].map(
            {k: v[metric] for k, v in reg_data.items()}
        ).fillna(0)

    # Is the listing likely legal? (entire home with high min_nights = more likely legal)
    df["likely_legal"] = (
        (df["minimum_nights_num"] >= 30) |  # Long-term stays are always legal
        (df.get("ll18_registration_rate", 0) > 0.3)  # High registration borough
    ).astype(int)

    df = df.drop(columns=["_borough_label"])
    return df


def main():
    print("=" * 60)
    print("PHASE 1c: HOLIDAY + DEMOGRAPHIC + REGULATION FEATURES")
    print("=" * 60)

    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)
    print(f"  Train: {len(train):,}, Test: {len(test):,}")

    # Add features
    train = add_holiday_features(train)
    test = add_holiday_features(test)

    train = add_demographic_features(train)
    test = add_demographic_features(test)

    train = add_regulation_features(train)
    test = add_regulation_features(test)

    # Update feature list
    with open(FEATURES_PATH) as f:
        meta = json.load(f)

    new_features = [
        "days_to_next_holiday", "days_since_last_holiday",
        "holidays_next_30d", "holidays_next_60d", "holidays_next_90d",
        "days_to_nyc_peak", "is_summer", "is_holiday_season",
        "borough_median_income", "borough_college_pct", "borough_renter_pct", "borough_pop_density",
        "ll18_registration_rate", "ll18_enforcement_level", "ll18_legal_risk", "likely_legal",
    ]

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

    print(f"\n✅ Holiday + demographic + regulation features added!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
