"""Comp-based revenue estimation from the market listings DB.

Generalizable by design: coverage is determined by *data density* (are there
enough comparable listings near the address?), not a hardcoded region list.
Any market loaded into the `listings` table is supported automatically — no
code changes needed to add a new city or state. Estimates use the real
`estimated_revenue_l365d` figures from InsideAirbnb rather than a model.
"""
import json
import math
from collections import Counter
from statistics import median

from .enrichment import (
    estimate_adr_occupancy, monthly_forecast, performance_drivers, confidence_reasons,
    amenity_multiplier, amenity_drivers,
)
from .scoring import compute_airworthy

MIN_COMPS = 5           # fewer than this within MAX_RADIUS_KM => no coverage
TARGET_COMPS = 25       # cap on comps used for the point estimate
MAX_RADIUS_KM = 30.0    # widest search ring
RADII_KM = (2.0, 5.0, 10.0, 20.0, 30.0)
# Winsorize revenue to tame extreme/mis-scaled outliers before averaging.
REV_MIN, REV_MAX = 1_000.0, 750_000.0


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _pretty_city(slug):
    return slug.replace("-", " ").title() if slug else "Unknown"


def _percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def covered_markets(conn):
    """Distinct states present in the DB, for honest 'no coverage' messaging."""
    rows = conn.execute(
        "SELECT DISTINCT state FROM listings WHERE state IS NOT NULL ORDER BY state"
    ).fetchall()
    return [r[0].upper() for r in rows]


DEMAND_CURVE_RADIUS_KM = 5.0   # tight ring — seasonality is hyper-local
DEMAND_CURVE_MIN_COMPS = 3
DEMAND_CURVE_MAX_COMPS = 25


def get_demand_curve(conn, lat, lng, bedrooms, room_type="Entire home/apt"):
    """Average 12-month booked-share seasonality curve for the nearest
    listings that actually have one, or None if there's no local coverage.

    This is independent of whichever comp set produced the revenue estimate
    (NYC's trained-model comps live in a separate index with a different id
    space) — it queries the shared listings DB directly by lat/lng, so it
    works the same way for every market that has demand_curve data and
    degrades to "no data" (None) everywhere else, e.g. NYC.
    """
    dlat = DEMAND_CURVE_RADIUS_KM / 111.0
    coslat = max(0.1, math.cos(math.radians(lat)))
    dlng = DEMAND_CURVE_RADIUS_KM / (111.0 * coslat)

    rows = conn.execute(
        """
        SELECT bedrooms, latitude, longitude, demand_curve
        FROM listings
        WHERE (state, city, snapshot_date) IN (
                SELECT state, city, MAX(snapshot_date) FROM listings GROUP BY state, city
              )
          AND room_type = ?
          AND demand_curve IS NOT NULL
          AND latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        """,
        (room_type, lat - dlat, lat + dlat, lng - dlng, lng + dlng),
    ).fetchall()
    if not rows:
        return None

    candidates = []
    for r in rows:
        d = _haversine_km(lat, lng, r["latitude"], r["longitude"])
        if d > DEMAND_CURVE_RADIUS_KM:
            continue
        try:
            curve = json.loads(r["demand_curve"])
        except (TypeError, ValueError):
            continue
        if not isinstance(curve, list) or len(curve) != 12:
            continue
        bed_sim = 1.0 / (1.0 + abs((r["bedrooms"] or bedrooms) - bedrooms))
        dist_w = 1.0 / (1.0 + d)
        candidates.append((dist_w * bed_sim, curve))

    if len(candidates) < DEMAND_CURVE_MIN_COMPS:
        return None

    candidates.sort(key=lambda c: -c[0])
    used = candidates[:DEMAND_CURVE_MAX_COMPS]
    wsum = sum(w for w, _ in used) or 1.0
    averaged = [
        sum(w * curve[i] for w, curve in used) / wsum
        for i in range(12)
    ]
    return [round(v, 4) for v in averaged]


def estimate_from_db(conn, lat, lng, bedrooms, accommodates, room_type="Entire home/apt",
                      nightly_rate=None, is_superhost=False, exclude_ids=None, amenities=None):
    """Return a comp-based estimate dict, or None if there's no local coverage.

    The returned dict mirrors the fields the API response needs (annual_revenue,
    confidence, comps, market, data_freshness, n_comps). `exclude_ids` drops
    specific comparable listing IDs before scoring, so callers can recompute
    the estimate after a user excludes a comp — without a new endpoint.
    """
    exclude_ids = set(exclude_ids or [])
    # Over-fetch a bounding box for the widest ring, then filter by true distance.
    dlat = MAX_RADIUS_KM / 111.0
    coslat = max(0.1, math.cos(math.radians(lat)))
    dlng = MAX_RADIUS_KM / (111.0 * coslat)

    rows = conn.execute(
        """
        SELECT id, city, state, bedrooms, accommodates, price_numeric,
               estimated_revenue_l365d AS rev, latitude, longitude,
               picture_url, listing_url
        FROM listings
        WHERE (state, city, snapshot_date) IN (
                SELECT state, city, MAX(snapshot_date) FROM listings GROUP BY state, city
              )
          AND room_type = ?
          AND estimated_revenue_l365d IS NOT NULL
          AND estimated_revenue_l365d > 0
          AND latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        """,
        (room_type, lat - dlat, lat + dlat, lng - dlng, lng + dlng),
    ).fetchall()
    if not rows:
        return None

    cand = []
    for r in rows:
        if exclude_ids and r["id"] in exclude_ids:
            continue
        d = _haversine_km(lat, lng, r["latitude"], r["longitude"])
        if d <= MAX_RADIUS_KM:
            cand.append((d, r))
    if len(cand) < MIN_COMPS:
        return None
    cand.sort(key=lambda x: x[0])

    # Adaptive radius: smallest ring yielding >= MIN_COMPS, preferring bedroom matches.
    chosen = None
    for radius in RADII_KM:
        within = [(d, r) for d, r in cand if d <= radius]
        bed_matched = [
            (d, r) for d, r in within
            if r["bedrooms"] is not None and abs(r["bedrooms"] - bedrooms) <= 1
        ]
        pool = bed_matched if len(bed_matched) >= MIN_COMPS else within
        if len(pool) >= MIN_COMPS:
            chosen = pool
            break
    if chosen is None:
        chosen = cand  # already within MAX_RADIUS_KM
    if len(chosen) < MIN_COMPS:
        return None

    scored = []
    for d, r in chosen:
        bed = r["bedrooms"] if r["bedrooms"] is not None else bedrooms
        acc = r["accommodates"] if r["accommodates"] is not None else accommodates
        bed_sim = 1.0 / (1.0 + abs(bed - bedrooms))
        acc_sim = 1.0 / (1.0 + abs(acc - accommodates) / 2.0)
        dist_w = 1.0 / (1.0 + d)
        score = dist_w * (0.6 * bed_sim + 0.4 * acc_sim)
        rev = min(max(float(r["rev"]), REV_MIN), REV_MAX)
        scored.append({"dist": d, "score": score, "rev": rev, "row": r})

    scored.sort(key=lambda s: (-s["score"], s["dist"]))
    used = scored[:TARGET_COMPS]

    # Similarity-weighted point estimate.
    wsum = sum(s["score"] for s in used) or 1.0
    pre_amenity_point = sum(s["score"] * s["rev"] for s in used) / wsum

    # Modal market among the comps used — also used to look up a
    # market-calibrated amenity impact below.
    (city_slug, state), _ = Counter(
        (s["row"]["city"], s["row"]["state"]) for s in used
    ).most_common(1)[0]
    city_label = f"{_pretty_city(city_slug)}, {state.upper()}"

    # Property-facts amenity adjustment (facts editor) — calibrated from
    # real listings in this city where the data supports it, else the state,
    # else a modest, disclosed heuristic uplift — applied after the
    # comp-weighted point estimate.
    point = pre_amenity_point * amenity_multiplier(amenities, market_state=state, city_slug=city_slug)

    # Data-driven interval from the comp revenue distribution (IQR).
    revs = sorted(s["rev"] for s in used)
    lower = _percentile(revs, 0.25)
    upper = _percentile(revs, 0.75)
    mean = sum(revs) / len(revs)
    var = sum((x - mean) ** 2 for x in revs) / len(revs)
    cv = (var ** 0.5) / mean if mean > 0 else 0.0

    n = len(used)
    if n >= 15 and cv < 0.6:
        level = "high"
    elif n >= 8 and cv < 1.2:
        level = "medium"
    else:
        level = "low"

    prices = sorted(
        float(s["row"]["price_numeric"]) for s in used
        if s["row"]["price_numeric"] is not None
    )
    median_price = median(prices) if prices else 0.0

    active = conn.execute(
        """SELECT COUNT(*) FROM listings
           WHERE state = ? AND city = ? AND room_type = ?
             AND estimated_revenue_l365d IS NOT NULL""",
        (state, city_slug, room_type),
    ).fetchone()[0]

    freshness = conn.execute(
        "SELECT MAX(snapshot_date) FROM listings WHERE state = ? AND city = ?",
        (state, city_slug),
    ).fetchone()[0]

    bed_matches = sum(
        1 for s in used
        if s["row"]["bedrooms"] is not None and int(s["row"]["bedrooms"]) == bedrooms
    )
    bedroom_match_ratio = bed_matches / n if n else 0.0
    avg_distance_km = sum(s["dist"] for s in used) / n if n else 0.0

    # Larger, ID-stable comparable list for an explorer UI — every comp
    # carries a plain-language reason for inclusion and a note on how it
    # differs from the subject property.
    comps_out = []
    for s in used[:20]:
        row = s["row"]
        comp_bedrooms = int(row["bedrooms"]) if row["bedrooms"] is not None else 0
        bed_diff = comp_bedrooms - bedrooms
        diff_bits = []
        if bed_diff != 0:
            diff_bits.append(f"{abs(bed_diff)} {'more' if bed_diff > 0 else 'fewer'} bedroom(s)")
        if s["dist"] > 1:
            diff_bits.append(f"{s['dist']:.1f} km away")
        reason_bits = []
        if bed_diff == 0:
            reason_bits.append("same bedroom count")
        if s["dist"] <= 2:
            reason_bits.append("nearby")
        if not reason_bits:
            reason_bits.append("closest available match")

        comps_out.append({
            "id": int(row["id"]),
            "distance_km": round(s["dist"], 2),
            "bedrooms": comp_bedrooms,
            "revenue": round(s["rev"], 0),
            "similarity_score": round(s["score"], 4),
            "borough": city_label,
            "price": float(row["price_numeric"]) if row["price_numeric"] is not None else None,
            "reason_included": ", ".join(reason_bits),
            "differences": ", ".join(diff_bits) if diff_bits else "closely matches this property",
            "picture_url": (row["picture_url"] or None) if "picture_url" in row.keys() else None,
            "listing_url": (row["listing_url"] or None) if "listing_url" in row.keys() else None,
        })

    nightly_rate_for_adr = nightly_rate if nightly_rate else median_price
    adr, occupancy = estimate_adr_occupancy(point, nightly_rate_for_adr)
    drivers = performance_drivers(
        nightly_rate=nightly_rate_for_adr,
        bedrooms=bedrooms,
        median_price=median_price,
        n_comps=n,
        is_superhost=is_superhost,
        avg_distance_km=avg_distance_km,
    )
    drivers = drivers + amenity_drivers(amenities, pre_amenity_point, market_state=state, city_slug=city_slug)
    reasons, weaknesses = confidence_reasons(
        n_comps=n,
        avg_distance_km=avg_distance_km,
        cv=cv,
        data_freshness=freshness or "",
        bedroom_match_ratio=bedroom_match_ratio,
    )

    airworthy = compute_airworthy(
        annual_revenue=point,
        benchmark_revenue=median(revs),
        cv=cv,
        n_comps=n,
    )

    return {
        "annual_revenue": round(point, 0),
        "airworthy_score": airworthy.score,
        "airworthy_verdict": airworthy.verdict,
        "airworthy_reason": airworthy.reason,
        "confidence": {
            "level": level,
            "revenue_lower": round(min(lower, point), 0),
            "revenue_upper": round(max(upper, point), 0),
            "cv": round(cv, 4),
            "reasons": reasons,
            "weaknesses": weaknesses,
        },
        "comps": comps_out,
        "market": {
            "borough": city_label,
            "median_revenue": round(median(revs), 0),
            "median_price": round(median_price, 0),
            "active_listings": int(active),
            "adr": adr,
            "occupancy_rate": occupancy,
        },
        "monthly_forecast": monthly_forecast(point, cv),
        "performance_drivers": drivers,
        "data_freshness": freshness,
        "n_comps": n,
    }
