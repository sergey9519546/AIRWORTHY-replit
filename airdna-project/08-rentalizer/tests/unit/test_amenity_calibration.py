"""Unit tests for amenity calibration caching and invalidation.

The calibration cache must not require a server restart to pick up newly
loaded market data: `get_calibration()` should notice when the newest
`snapshot_date` in the listings table has advanced and recompute, while
still avoiding a full table scan on every call when nothing changed.
"""
import sqlite3

import pytest

from src import amenity_calibration as ac


def _make_db(tmp_path, rows, snapshot_date="2026-01-01"):
    db_path = tmp_path / "airbnb.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE listings (
            state TEXT,
            city TEXT,
            bedrooms REAL,
            estimated_revenue_l365d REAL,
            amenities TEXT,
            snapshot_date TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO listings (state, city, bedrooms, estimated_revenue_l365d, amenities, snapshot_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (state, city, bedrooms, rev, amenities, snapshot_date)
            for state, city, bedrooms, rev, amenities in rows
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def _pool_rows(n_with, n_without, rev_with=4000.0, rev_without=2000.0):
    rows = []
    for _ in range(n_with):
        rows.append(("ca", "los-angeles", 2, rev_with, "Pool, Wifi, Kitchen"))
    for _ in range(n_without):
        rows.append(("ca", "los-angeles", 2, rev_without, "Wifi, Kitchen"))
    return rows


class _ImmediateThread:
    """Stand-in for threading.Thread that runs the target synchronously on
    .start(), so tests can deterministically observe the result of a
    background recompute instead of racing a real thread."""

    def __init__(self, target=None, name=None, daemon=None):
        self._target = target

    def start(self):
        self._target()

    def join(self, timeout=None):
        pass


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    """Calibration is cached at module scope; isolate each test, and make
    the background recompute thread run inline so tests are deterministic."""
    monkeypatch.setattr(ac.threading, "Thread", _ImmediateThread)
    ac._calibration_cache = None
    ac._calibration_cache_snapshot = None
    ac._calibration_computing_snapshot = None
    yield
    ac._calibration_cache = None
    ac._calibration_cache_snapshot = None
    ac._calibration_computing_snapshot = None


def test_get_calibration_computes_data_backed_entry(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, _pool_rows(40, 40))
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()  # first call: cache is empty, kicks off recompute
    calibration = ac.get_calibration()  # second call: sees the fresh cache

    entry = calibration["states"]["ca"]["pool"]
    assert entry["is_data_backed"] is True
    assert entry["impact_pct"] > 0


def test_repeated_calls_reuse_cache_without_recompute(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, _pool_rows(40, 40))
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    calls = []
    real_compute = ac.compute_calibration

    def _tracked_compute(conn):
        calls.append(1)
        return real_compute(conn)

    monkeypatch.setattr(ac, "compute_calibration", _tracked_compute)

    ac.get_calibration()  # kicks off the one-and-only recompute
    first = ac.get_calibration()
    second = ac.get_calibration()

    assert first is second
    assert len(calls) == 1


def test_new_snapshot_date_invalidates_cache(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, _pool_rows(40, 40), snapshot_date="2026-01-01")
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()
    first = ac.get_calibration()
    assert first["states"]["ca"]["pool"]["is_data_backed"] is True

    # Simulate a fresh market-data load: newer snapshot_date, and this time
    # not enough listings on both sides to calibrate pool for ca.
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE listings SET snapshot_date = '2026-02-01'")
    conn.execute("DELETE FROM listings WHERE amenities LIKE 'Pool%'")
    conn.commit()
    conn.close()

    ac.get_calibration()  # notices the new snapshot_date, kicks off recompute
    second = ac.get_calibration()

    assert second is not first
    assert second["states"]["ca"]["pool"]["is_data_backed"] is False


def test_same_snapshot_date_does_not_invalidate_despite_new_rows(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, _pool_rows(20, 20), snapshot_date="2026-01-01")
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()
    first = ac.get_calibration()

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO listings (state, city, bedrooms, estimated_revenue_l365d, amenities, snapshot_date) "
        "VALUES ('ny', 'new-york-city', 2, 5000, 'Pool', '2026-01-01')"
    )
    conn.commit()
    conn.close()

    second = ac.get_calibration()

    # Same snapshot_date -> stale cache is intentionally reused; "ny" should
    # not show up until a new snapshot_date triggers a recompute.
    assert second is first
    assert "ny" not in second["states"]
