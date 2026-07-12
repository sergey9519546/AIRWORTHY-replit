"""Comp-based (DB) estimator: coverage is data-driven, not region-hardcoded."""
import os
import sqlite3

import pytest

from src.api import MAP_DB_PATH
from src.market_estimator import estimate_from_db, covered_markets


def _conn():
    if not os.path.exists(MAP_DB_PATH):
        pytest.skip("map DB not present in this environment")
    c = sqlite3.connect(MAP_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def test_estimate_in_covered_market():
    conn = _conn()
    try:
        r = estimate_from_db(conn, 34.10, -118.33, bedrooms=2, accommodates=4)  # LA
    finally:
        conn.close()
    assert r is not None
    assert r["annual_revenue"] > 0
    lo = r["confidence"]["revenue_lower"]
    hi = r["confidence"]["revenue_upper"]
    assert lo <= r["annual_revenue"] <= hi  # point always inside the range
    assert r["n_comps"] >= 5
    assert "CA" in r["market"]["borough"]


def test_uncovered_area_returns_none():
    conn = _conn()
    try:
        r = estimate_from_db(conn, 41.88, -87.63, bedrooms=2, accommodates=4)  # Chicago
    finally:
        conn.close()
    assert r is None  # no bogus number for areas with no data


def test_covered_markets_reports_states():
    conn = _conn()
    try:
        markets = covered_markets(conn)
    finally:
        conn.close()
    assert "CA" in markets and "FL" in markets
