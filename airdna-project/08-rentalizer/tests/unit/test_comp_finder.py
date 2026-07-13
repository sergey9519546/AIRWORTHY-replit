"""Regression tests for comp_finder index construction."""
import os
import time

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


def test_market_stats_refresh_when_training_csv_changes_on_disk(tmp_path):
    """A refreshed training CSV (e.g. from a data-reload script) should be
    picked up on the next call, without requiring a process restart."""
    csv_path = tmp_path / "train.csv"

    df_v1 = _tiny_train_df(["Entire home/apt"] * 5)
    df_v1["revenue"] = 10_000.0
    df_v1.to_csv(csv_path, index=False)
    comp_finder.build_index(pd.read_csv(csv_path), source_path=str(csv_path))

    stats_v1 = comp_finder.get_market_stats("Manhattan")
    assert stats_v1["median_revenue"] == 10_000.0

    # Ensure the new mtime is observably different, then rewrite the CSV
    # with a new revenue figure, simulating a fresh data load.
    time.sleep(0.01)
    df_v2 = _tiny_train_df(["Entire home/apt"] * 5)
    df_v2["revenue"] = 99_000.0
    df_v2.to_csv(csv_path, index=False)
    os.utime(csv_path, None)

    stats_v2 = comp_finder.get_market_stats("Manhattan")
    assert stats_v2["median_revenue"] == 99_000.0


def test_market_stats_do_not_rebuild_when_csv_unchanged(tmp_path, monkeypatch):
    """No rebuild (and thus no KD-Tree reconstruction) should happen when the
    training data file hasn't changed since the last build."""
    csv_path = tmp_path / "train.csv"
    df = _tiny_train_df(["Entire home/apt"] * 5)
    df.to_csv(csv_path, index=False)
    comp_finder.build_index(pd.read_csv(csv_path), source_path=str(csv_path))

    calls = []
    real_build_index = comp_finder.build_index

    def _spy(*args, **kwargs):
        calls.append(1)
        return real_build_index(*args, **kwargs)

    monkeypatch.setattr(comp_finder, "build_index", _spy)

    comp_finder.get_market_stats("Manhattan")
    comp_finder.find_comps(40.75, -73.98, 1, 2)

    assert calls == []
