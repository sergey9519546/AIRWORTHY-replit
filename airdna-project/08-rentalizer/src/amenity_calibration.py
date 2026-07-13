"""Data-derived amenity revenue impact, calibrated from the listings DB.

For each amenity toggle in the property-facts editor, we compare the average
annual revenue of listings that report the amenity (via InsideAirbnb's
free-text `amenities` field) against listings that don't, within the same
bedroom-count bucket (to avoid the comparison just reflecting "amenity X
correlates with bigger homes"). Buckets are recombined into a single
per-amenity percentage, weighted by how many listings back each bucket.

Calibration is computed at two grains:
  - per state (e.g. "ca"), and
  - per city within a state (e.g. "ca"/"los-angeles"),
using the same minimum-sample thresholds for both. `lookup()` prefers the
city-level figure when a city has enough listings on both sides of the
with/without split, since large cities within a state can have very
different amenity economics than the state as a whole. It falls back to
the state-level figure, and callers should fall back further to the fixed
heuristic in `enrichment.AMENITIES` (disclosed as a rough estimate rather
than presented as data-backed) when neither has enough support.
"""
import os
import re
import sqlite3
from functools import lru_cache

# Bedroom buckets used to control for the "bigger homes have more amenities
# AND more revenue" confound: 0-1, 2, 3, 4+.
def _bedroom_bucket(bedrooms):
    if bedrooms is None:
        return None
    try:
        b = int(round(float(bedrooms)))
    except (TypeError, ValueError):
        return None
    return min(4, max(0, b))


# Keyword matchers against the lowercased raw `amenities` text. These are
# substring/regex checks on InsideAirbnb's free-text amenity list, so they
# need to be specific enough to avoid false positives (e.g. "pool" should
# not match "pool table" or "whirlpool").
_PARKING_RE = re.compile(r"free[a-z ]*parking")


def _has_pool(text):
    return "pool" in text and "whirlpool" not in text and "pool table" not in text


AMENITY_MATCHERS = {
    "pool": _has_pool,
    "hot_tub": lambda t: "hot tub" in t,
    "parking": lambda t: bool(_PARKING_RE.search(t)),
    "ev_charger": lambda t: "ev charger" in t,
    "gym": lambda t: "gym" in t or "exercise equipment" in t,
    "pet_friendly": lambda t: "pets allowed" in t,
    "workspace": lambda t: "dedicated workspace" in t,
}

# A market-level calibration is only trusted if both sides of the
# with/without comparison have enough listings backing them.
MIN_BUCKET_N = 15
MIN_MARKET_WEIGHT = 30
# Clamp calibrated percentages to a plausible range; the raw comparison can
# be skewed by remaining confounds (location, host quality, etc.) that
# bedroom-bucketing doesn't fully control for.
CLAMP_MIN, CLAMP_MAX = -0.30, 0.60


def _db_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "db", "airbnb.db",
    )


def _resolve_group(accum_by_bucket, key):
    """Combine per-bucket with/without sums for one (group, amenity) into a
    single weighted calibration entry, or an undercalibrated placeholder."""
    weighted_pct_sum = 0.0
    weight_total = 0
    n_with_total = 0
    n_without_total = 0
    for bucket, sides in accum_by_bucket.items():
        sum_with, n_with = sides["with"]
        sum_without, n_without = sides["without"]
        n_with_total += n_with
        n_without_total += n_without
        if n_with < MIN_BUCKET_N or n_without < MIN_BUCKET_N:
            continue
        mean_with = sum_with / n_with
        mean_without = sum_without / n_without
        if mean_without <= 0:
            continue
        pct = (mean_with / mean_without) - 1.0
        weight = min(n_with, n_without)
        weighted_pct_sum += pct * weight
        weight_total += weight

    if weight_total >= MIN_MARKET_WEIGHT:
        impact_pct = weighted_pct_sum / weight_total
        impact_pct = max(CLAMP_MIN, min(CLAMP_MAX, impact_pct))
        return {
            "impact_pct": round(impact_pct, 4),
            "n_with": n_with_total,
            "n_without": n_without_total,
            "is_data_backed": True,
        }
    return {
        "impact_pct": None,
        "n_with": n_with_total,
        "n_without": n_without_total,
        "is_data_backed": False,
    }


def compute_calibration(conn):
    """Return {"states": {state: {amenity_key: entry}},
               "cities": {(state, city): {amenity_key: entry}}}.

    Each entry is {impact_pct, n_with, n_without, is_data_backed}. Reads the
    full listings table once; callers should cache the result (see
    `get_calibration` below) rather than recomputing per request.
    """
    rows = conn.execute(
        """
        SELECT state, city, bedrooms, estimated_revenue_l365d AS rev, amenities
        FROM listings
        WHERE estimated_revenue_l365d IS NOT NULL
          AND estimated_revenue_l365d > 0
          AND amenities IS NOT NULL AND amenities != ''
          AND state IS NOT NULL
        """
    ).fetchall()

    # state_accum[state][amenity][bucket]["with"/"without"] = [sum_rev, n]
    # city_accum[(state, city)][amenity][bucket][...] = [sum_rev, n]
    state_accum = {}
    city_accum = {}
    for r in rows:
        state = r["state"].lower()
        bucket = _bedroom_bucket(r["bedrooms"])
        if bucket is None:
            continue
        rev = float(r["rev"])
        text = r["amenities"].lower()
        city = r["city"].lower() if r["city"] else None

        state_acc = state_accum.setdefault(state, {})
        city_key = (state, city) if city else None
        city_acc = city_accum.setdefault(city_key, {}) if city_key else None

        for key, matcher in AMENITY_MATCHERS.items():
            side = "with" if matcher(text) else "without"

            bucket_acc = state_acc.setdefault(key, {}).setdefault(
                bucket, {"with": [0.0, 0], "without": [0.0, 0]}
            )
            bucket_acc[side][0] += rev
            bucket_acc[side][1] += 1

            if city_acc is not None:
                city_bucket_acc = city_acc.setdefault(key, {}).setdefault(
                    bucket, {"with": [0.0, 0], "without": [0.0, 0]}
                )
                city_bucket_acc[side][0] += rev
                city_bucket_acc[side][1] += 1

    states = {}
    for state, amenities in state_accum.items():
        states[state] = {
            key: _resolve_group(buckets, key) for key, buckets in amenities.items()
        }

    cities = {}
    for city_key, amenities in city_accum.items():
        cities[city_key] = {
            key: _resolve_group(buckets, key) for key, buckets in amenities.items()
        }

    return {"states": states, "cities": cities}


_calibration_cache = None
_calibration_cache_snapshot = None


def _latest_snapshot_date(conn):
    row = conn.execute("SELECT MAX(snapshot_date) AS d FROM listings").fetchone()
    return row["d"] if row else None


def get_calibration():
    """Lazily compute and cache amenity calibration, keyed by the newest
    `snapshot_date` present in the listings table.

    Recomputing the full calibration is a single full-table scan, so we
    avoid it on every request. But we also can't just cache it forever: new
    market data can be loaded into the DB (via `scripts/load_data.py`)
    without a server restart, and that data carries a new `snapshot_date`.
    So on every call we run a cheap `MAX(snapshot_date)` check (same
    freshness signal `/api/cities` already exposes to the frontend) and only
    redo the expensive full scan when that value has changed.
    """
    global _calibration_cache, _calibration_cache_snapshot

    db_path = _db_path()
    if not os.path.exists(db_path):
        _calibration_cache = {}
        _calibration_cache_snapshot = None
        return _calibration_cache

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        latest = _latest_snapshot_date(conn)
        if _calibration_cache is not None and latest == _calibration_cache_snapshot:
            return _calibration_cache

        _calibration_cache = compute_calibration(conn)
        _calibration_cache_snapshot = latest
    finally:
        conn.close()
    return _calibration_cache


def lookup(state, amenity_key, city_slug=None):
    """Return a calibrated entry for (state, amenity_key), preferring a
    city-level figure over the state-level one when the city has enough
    listings to support its own with/without comparison. Returns None if
    neither has market data support (caller should fall back to a fixed
    heuristic)."""
    if not state:
        return None
    calibration = get_calibration()

    if city_slug:
        city_entry = calibration.get("cities", {}).get(
            (state.lower(), city_slug.lower()), {}
        ).get(amenity_key)
        if city_entry and city_entry["is_data_backed"]:
            return city_entry

    state_entry = calibration.get("states", {}).get(state.lower(), {}).get(amenity_key)
    if state_entry and state_entry["is_data_backed"]:
        return state_entry
    return None
