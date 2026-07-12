"""Unit tests for the seasonal demand-curve ETL aggregation.

The demand curve replaces the old lifetime-review-count proxy with a real
month-by-month booked-share derived from each listing's forward calendar.
"""
import gzip
import importlib.util
import io
import os
import tempfile

import pytest

# Load scripts/load_demand_curves.py (repo-root/scripts, sibling of 08-rentalizer).
_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "scripts",
    "load_demand_curves.py",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("load_demand_curves", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_calendar(rows):
    """rows: list of (listing_id, date, available) -> path to a gz calendar."""
    buf = io.StringIO()
    buf.write("listing_id,date,available,minimum_nights,maximum_nights\n")
    for lid, date, avail in rows:
        buf.write(f"{lid},{date},{avail},2,365\n")
    fd, path = tempfile.mkstemp(suffix="_calendar.csv.gz")
    os.close(fd)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return path


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def test_booked_share_computed_per_month(mod):
    # Listing 1: January has 2 booked ('f') of 4 nights -> 0.5; July fully open -> 0.0
    rows = [
        (1, "2026-01-01", "f"),
        (1, "2026-01-02", "f"),
        (1, "2026-01-03", "t"),
        (1, "2026-01-04", "t"),
        (1, "2026-07-01", "t"),
        (1, "2026-07-02", "t"),
    ]
    path = _write_calendar(rows)
    try:
        curves = mod.aggregate_curves(path)
    finally:
        os.remove(path)

    assert 1 in curves
    curve = curves[1]
    assert len(curve) == 12
    assert curve[0] == 0.5      # January index 0
    assert curve[6] == 0.0      # July index 6
    assert curve[1] is None     # February had no data -> None, not a fake value


def test_months_combined_across_years(mod):
    # Same calendar month across two years is combined into one seasonal bucket.
    rows = [
        (7, "2026-06-01", "f"),   # booked
        (7, "2027-06-01", "t"),   # open
    ]
    path = _write_calendar(rows)
    try:
        curves = mod.aggregate_curves(path)
    finally:
        os.remove(path)

    # June index 5: 1 booked of 2 total -> 0.5
    assert curves[7][5] == 0.5


def test_available_flag_is_case_and_space_insensitive(mod):
    rows = [
        (9, "2026-03-01", " F "),  # padded/upper -> still booked
        (9, "2026-03-02", "t"),
    ]
    path = _write_calendar(rows)
    try:
        curves = mod.aggregate_curves(path)
    finally:
        os.remove(path)
    assert curves[9][2] == 0.5  # March index 2
