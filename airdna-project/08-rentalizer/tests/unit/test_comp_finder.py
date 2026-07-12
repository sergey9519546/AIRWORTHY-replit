"""Regression tests for comp_finder index construction."""
import pandas as pd

from src import comp_finder


def _tiny_train_df(room_types):
    """Build a minimal training frame matching the columns build_index reads."""
    n = len(room_types)
    return pd.DataFrame({
        "id": list(range(n)),
        "latitude": [40.75 + i * 0.001 for i in range(n)],
        "longitude": [-73.98 - i * 0.001 for i in range(n)],
        "bedrooms_num": [1] * n,
        "bathrooms_num": [1.0] * n,
        "accommodates_num": [2] * n,
        "price_num": [150.0] * n,
        "revenue": [50000.0] * n,
        "room_type": room_types,
        "borough_Manhattan": [1] * n,
    })


def test_build_index_preserves_room_type_from_rows():
    """room_type must come from the training row, not a hardcoded constant."""
    df = _tiny_train_df(["Entire home/apt", "Private room", "Hotel room"])
    comp_finder.build_index(df)

    listings = comp_finder._listings
    assert listings is not None
    got = {l["room_type"] for l in listings}
    assert got == {"Entire home/apt", "Private room", "Hotel room"}


def test_build_index_defaults_room_type_when_missing():
    """If the column is absent, fall back to the documented default."""
    df = _tiny_train_df(["Entire home/apt"]).drop(columns=["room_type"])
    comp_finder.build_index(df)

    listings = comp_finder._listings
    assert listings is not None
    assert all(l["room_type"] == "Entire home/apt" for l in listings)
