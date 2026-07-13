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


def test_lookup_prefers_city_when_city_has_enough_listings(tmp_path, monkeypatch):
    """When the city itself has enough listings on both sides of the
    with/without split, lookup() must return the city-level entry, not
    silently fall back to the state-level one."""
    rows = _pool_rows(40, 40, rev_with=5000.0, rev_without=2000.0)
    # Pad in some other-city ca listings with a different (state-level)
    # pool impact, so the state and city entries are distinguishable.
    rows += [
        ("ca", "sacramento", 2, 3000.0, "Pool, Wifi") for _ in range(40)
    ] + [
        ("ca", "sacramento", 2, 2500.0, "Wifi") for _ in range(40)
    ]
    db_path = _make_db(tmp_path, rows)
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()

    entry = ac.lookup("ca", "pool", city_slug="los-angeles")

    assert entry is not None
    assert entry["is_data_backed"] is True
    calibration = ac.get_calibration()
    city_entry = calibration["cities"][("ca", "los-angeles")]["pool"]
    state_entry = calibration["states"]["ca"]["pool"]
    assert entry == city_entry
    assert entry != state_entry


def test_lookup_falls_back_to_state_when_city_undersupported(tmp_path, monkeypatch):
    """When the city doesn't have enough listings on both sides, but the
    state as a whole does, lookup() must fall back to the state-level
    entry rather than returning None or an undercalibrated city figure."""
    # Only a handful of los-angeles listings (below MIN_BUCKET_N), but
    # plenty of other ca listings to support a state-level calibration.
    rows = _pool_rows(5, 5)
    rows += [
        ("ca", "sacramento", 2, 4000.0, "Pool, Wifi") for _ in range(40)
    ] + [
        ("ca", "sacramento", 2, 2000.0, "Wifi") for _ in range(40)
    ]
    db_path = _make_db(tmp_path, rows)
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()

    entry = ac.lookup("ca", "pool", city_slug="los-angeles")

    assert entry is not None
    calibration = ac.get_calibration()
    state_entry = calibration["states"]["ca"]["pool"]
    assert entry == state_entry
    assert state_entry["is_data_backed"] is True
    city_entry = calibration["cities"].get(("ca", "los-angeles"), {}).get("pool")
    assert city_entry is None or city_entry["is_data_backed"] is False


def test_lookup_returns_none_when_neither_city_nor_state_supported(tmp_path, monkeypatch):
    """When neither the city nor the state has enough listings to support
    a calibration, lookup() must return None so callers fall back to the
    fixed heuristic instead of fabricating a figure."""
    rows = _pool_rows(5, 5)
    db_path = _make_db(tmp_path, rows)
    monkeypatch.setattr(ac, "_db_path", lambda: str(db_path))

    ac.get_calibration()

    entry = ac.lookup("ca", "pool", city_slug="los-angeles")

    assert entry is None


def test_resolve_group_clamps_raw_pct_above_max():
    """A raw weighted percentage above CLAMP_MAX must be clamped, not
    passed through raw -- otherwise a confound (or a bug) could ship an
    implausible 100%+ amenity price bump."""
    accum = {
        1: {"with": [2000.0 * 30, 30], "without": [1000.0 * 30, 30]},  # raw pct = 1.0
    }

    entry = ac._resolve_group(accum, "pool")

    assert entry["is_data_backed"] is True
    assert entry["impact_pct"] == ac.CLAMP_MAX


def test_resolve_group_clamps_raw_pct_below_min():
    """A raw weighted percentage below CLAMP_MIN must be clamped up rather
    than reported as an implausibly large negative impact."""
    accum = {
        1: {"with": [500.0 * 30, 30], "without": [1000.0 * 30, 30]},  # raw pct = -0.5
    }

    entry = ac._resolve_group(accum, "pool")

    assert entry["is_data_backed"] is True
    assert entry["impact_pct"] == ac.CLAMP_MIN


def test_resolve_group_weights_multiple_buckets_not_just_largest():
    """Buckets must be combined via a weight-averaged percentage, not by
    letting the bucket with the most listings simply win outright."""
    accum = {
        # bucket 1: pct = 0.10, weight 20
        1: {"with": [1100.0 * 20, 20], "without": [1000.0 * 20, 20]},
        # bucket 3: pct = 0.30, weight 40
        3: {"with": [1300.0 * 40, 40], "without": [1000.0 * 40, 40]},
    }

    entry = ac._resolve_group(accum, "pool")

    assert entry["is_data_backed"] is True
    # Weighted average: (0.10*20 + 0.30*40) / 60 = 0.2333...
    assert entry["impact_pct"] == pytest.approx(0.2333, abs=1e-4)
    # Must not equal the pct of either individual bucket (i.e. must not
    # have just picked the largest-weight bucket's own percentage).
    assert entry["impact_pct"] != 0.30
    assert entry["impact_pct"] != 0.10


def test_resolve_group_bucket_below_min_bucket_n_is_excluded_entirely():
    """A bucket with fewer than MIN_BUCKET_N listings on either side must
    contribute nothing to the combined weight -- not even partial credit --
    so it can't be used to sneak a market over MIN_MARKET_WEIGHT."""
    below = ac.MIN_BUCKET_N - 1
    accum = {
        # Well-supported bucket, but alone it doesn't reach MIN_MARKET_WEIGHT.
        1: {"with": [2000.0 * ac.MIN_BUCKET_N, ac.MIN_BUCKET_N],
            "without": [1000.0 * ac.MIN_BUCKET_N, ac.MIN_BUCKET_N]},
        # Under-supported bucket with a huge n_without that should NOT
        # count towards weight_total, since n_with is below MIN_BUCKET_N.
        3: {"with": [2000.0 * below, below],
            "without": [1000.0 * 100, 100]},
    }

    entry = ac._resolve_group(accum, "pool")

    assert entry["is_data_backed"] is False
    assert entry["impact_pct"] is None
    # n totals still reflect all rows seen, even the excluded bucket.
    assert entry["n_with"] == ac.MIN_BUCKET_N + below
    assert entry["n_without"] == ac.MIN_BUCKET_N + 100


def test_resolve_group_at_min_market_weight_boundary():
    """Combined weight exactly at MIN_MARKET_WEIGHT must be data-backed;
    one listing short of it (on either side of one bucket) must not be."""
    half = ac.MIN_MARKET_WEIGHT // 2
    assert half >= ac.MIN_BUCKET_N, "test assumes half a market's weight still clears MIN_BUCKET_N"

    accum_at_threshold = {
        1: {"with": [2000.0 * half, half], "without": [1000.0 * half, half]},
        3: {"with": [2000.0 * half, half], "without": [1000.0 * half, half]},
    }
    entry_at = ac._resolve_group(accum_at_threshold, "pool")
    assert entry_at["is_data_backed"] is True

    # Shrink one bucket below MIN_BUCKET_N so it's excluded entirely,
    # dropping weight_total below MIN_MARKET_WEIGHT.
    below = ac.MIN_BUCKET_N - 1
    accum_below_threshold = {
        1: {"with": [2000.0 * half, half], "without": [1000.0 * half, half]},
        3: {"with": [2000.0 * below, below], "without": [1000.0 * below, below]},
    }
    entry_below = ac._resolve_group(accum_below_threshold, "pool")
    assert entry_below["is_data_backed"] is False
    assert entry_below["impact_pct"] is None


# --- AMENITY_MATCHERS: keyword heuristics against free-text amenities -------
#
# Each matcher runs against a lowercased raw `amenities` string. These tests
# cover a true positive, a true negative, and the known false-positive traps
# called out in the source comments (e.g. "whirlpool" is not a pool, "paid
# parking" is not free parking) for every entry in AMENITY_MATCHERS.


class TestPoolMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["pool"](t))

    def test_true_positive(self):
        assert self.matcher("pool, wifi, kitchen") is True

    def test_true_negative(self):
        assert self.matcher("wifi, kitchen, air conditioning") is False

    def test_whirlpool_is_not_a_pool(self):
        assert self.matcher("whirlpool tub, wifi") is False

    def test_pool_table_is_not_a_pool(self):
        assert self.matcher("pool table, wifi") is False

    def test_pool_alongside_whirlpool_is_correctly_a_pool(self):
        # A listing that genuinely lists both a pool and a whirlpool tub
        # separately must still count as having a pool -- the "whirlpool"
        # exclusion is scoped to that specific occurrence, not a blanket
        # substring check over the whole text.
        assert self.matcher("pool, whirlpool tub, wifi") is True


class TestHotTubMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["hot_tub"](t))

    def test_true_positive(self):
        assert self.matcher("hot tub, wifi, kitchen") is True

    def test_true_negative(self):
        assert self.matcher("pool, wifi, kitchen") is False

    def test_hot_water_is_not_a_hot_tub(self):
        assert self.matcher("hot water, wifi") is False


class TestParkingMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["parking"](t))

    def test_true_positive_free_parking(self):
        assert self.matcher("free parking on premises") is True

    def test_true_positive_free_street_parking(self):
        assert self.matcher("free street parking") is True

    def test_true_negative_no_parking_mentioned(self):
        assert self.matcher("wifi, kitchen, air conditioning") is False

    def test_paid_parking_is_not_free_parking(self):
        assert self.matcher("paid parking on premises") is False

    def test_parking_without_free_qualifier_does_not_match(self):
        assert self.matcher("parking available") is False


class TestEvChargerMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["ev_charger"](t))

    def test_true_positive(self):
        assert self.matcher("ev charger, wifi") is True

    def test_true_negative(self):
        assert self.matcher("free parking, wifi") is False

    def test_generic_charger_is_not_an_ev_charger(self):
        assert self.matcher("phone charger, wifi") is False


class TestGymMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["gym"](t))

    def test_true_positive_gym_keyword(self):
        assert self.matcher("gym, wifi, kitchen") is True

    def test_true_positive_exercise_equipment_keyword(self):
        assert self.matcher("exercise equipment, wifi") is True

    def test_true_negative(self):
        assert self.matcher("wifi, kitchen, pool") is False


class TestPetFriendlyMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["pet_friendly"](t))

    def test_true_positive(self):
        assert self.matcher("pets allowed, wifi") is True

    def test_true_negative(self):
        assert self.matcher("wifi, kitchen") is False

    def test_pet_friendly_wording_alone_does_not_match(self):
        # Only the exact "pets allowed" InsideAirbnb phrasing is matched;
        # a differently-worded mention should not false-positive.
        assert self.matcher("pet friendly building") is False


class TestWorkspaceMatcher:
    matcher = staticmethod(lambda t: ac.AMENITY_MATCHERS["workspace"](t))

    def test_true_positive(self):
        assert self.matcher("dedicated workspace, wifi") is True

    def test_true_negative(self):
        assert self.matcher("wifi, kitchen") is False

    def test_generic_desk_is_not_a_dedicated_workspace(self):
        assert self.matcher("desk, wifi") is False


@pytest.mark.parametrize("key", list(ac.AMENITY_MATCHERS.keys()))
def test_every_matcher_key_is_callable_and_boolean(key):
    """Guard against a future matcher returning a non-bool (e.g. a Match
    object from a bare `re.search` instead of `bool(...)`), which would
    silently corrupt the "with"/"without" split via truthiness quirks."""
    matcher = ac.AMENITY_MATCHERS[key]
    assert isinstance(matcher("some plain text with no amenities"), bool)
