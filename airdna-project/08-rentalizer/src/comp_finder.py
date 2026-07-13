"""Comparable listing finder using KD-Tree."""
import logging
import os
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy.spatial import KDTree

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class Comp:
    listing_id: int
    lat: float
    lng: float
    bedrooms: int
    bathrooms: float
    accommodates: int
    room_type: str
    price: float
    revenue: float
    borough: str
    distance_km: float
    score: float
    picture_url: str | None = None
    listing_url: str | None = None


# Global state
_tree: KDTree | None = None
_train_data: pd.DataFrame | None = None
_listings: list[dict] | None = None

# Path the training data was loaded from (if any) and the mtime it had at
# last build, so we can detect when a fresh CSV has been dropped in (e.g. by
# a data-refresh script) and rebuild without requiring a process restart.
# Train.csv carries no snapshot_date column of its own, so file mtime is the
# freshness signal here — mirroring the cheap-check/expensive-rebuild
# pattern `amenity_calibration.get_calibration()` uses for the listings DB.
_train_data_path: str | None = None
_train_data_mtime: float | None = None


def build_index(train_df: pd.DataFrame, source_path: str | None = None):
    """Build KD-Tree index from training data.

    `source_path`, if given, is remembered so later calls to `find_comps()`
    / `get_market_stats()` can detect (via mtime) when the file has been
    refreshed on disk and rebuild the index automatically.
    """
    global _tree, _train_data, _listings, _train_data_path, _train_data_mtime

    _train_data = train_df.copy()
    _train_data_path = source_path
    _train_data_mtime = _mtime(source_path) if source_path else None

    # Extract coordinates (convert to radians for haversine)
    coords = np.radians(train_df[["latitude", "longitude"]].values)
    _tree = KDTree(coords)

    # Pre-build listing dicts for fast lookup (vectorized, no iterrows)
    _listings = []
    records = train_df.to_dict('records')
    for row in records:
        _listings.append({
            "id": row.get("id", 0),
            "lat": row["latitude"],
            "lng": row["longitude"],
            "bedrooms": int(row.get("bedrooms_num", 0)),
            "bathrooms": float(row.get("bathrooms_num", 1)),
            "accommodates": int(row.get("accommodates_num", 2)),
            "room_type": row.get("room_type", "Entire home/apt"),
            "price": float(row["price_num"]),
            "revenue": float(row["revenue"]),
            "borough": _get_borough(row),
            "picture_url": (row.get("picture_url") or None),
            "listing_url": (row.get("listing_url") or None),
        })

    # Pre-compute market stats per borough at startup
    _precompute_market_stats(train_df)

    logger.info(f"Built KD-Tree index with {len(_listings)} listings")


def _mtime(path: str) -> float | None:
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _ensure_fresh():
    """Rebuild the index if the training CSV has changed on disk since the
    last build. A no-op (single cheap stat call) when nothing has changed,
    so this is safe to call on every request."""
    if not _train_data_path:
        return
    current = _mtime(_train_data_path)
    if current is not None and current != _train_data_mtime:
        logger.info(f"Detected updated training data at {_train_data_path}, rebuilding comp index")
        build_index(pd.read_csv(_train_data_path), source_path=_train_data_path)


def _get_borough(row):
    """Extract borough label from one-hot encoded columns."""
    for col in ["borough_Manhattan", "borough_Brooklyn", "borough_Queens", "borough_Bronx", "borough_Staten Island"]:
        if row.get(col, 0) == 1:
            return col.replace("borough_", "")
    return "Unknown"


def find_comps(lat: float, lng: float, bedrooms: int, accommodates: int, bathrooms: int = 1, k: int = 20,
               exclude_ids: set | None = None) -> list[Comp]:
    """Find k nearest comparable listings. `exclude_ids` drops specific
    listing IDs before scoring, so a caller can recompute after a user
    excludes a comparable from the set."""
    _ensure_fresh()
    if _tree is None or _listings is None:
        raise RuntimeError("Index not built. Call build_index() first.")

    exclude_ids = exclude_ids or set()


    # Query KD-Tree (haversine distance in radians)
    query = np.radians([[lat, lng]])
    distances, indices = _tree.query(query, k=min(k * 3, len(_listings)))

    distances = distances[0]
    indices = indices[0]

    # Convert haversine radians to km (Earth radius ~6371 km)
    distances_km = distances * 6371

    # Build comps with filtering and scoring
    comps = []
    for dist_km, idx in zip(distances_km, indices):
        listing = _listings[idx]

        if listing["id"] in exclude_ids:
            continue

        # Filter: bedrooms within ±1
        if abs(listing["bedrooms"] - bedrooms) > 1:
            continue

        # Filter: accommodates within ±2
        if abs(listing["accommodates"] - accommodates) > 2:
            continue

        # Score
        score = _score_comp(listing, dist_km, bedrooms, bathrooms, accommodates)

        comps.append(Comp(
            listing_id=listing["id"],
            lat=listing["lat"],
            lng=listing["lng"],
            bedrooms=listing["bedrooms"],
            bathrooms=listing["bathrooms"],
            accommodates=listing["accommodates"],
            room_type=listing["room_type"],
            price=listing["price"],
            revenue=listing["revenue"],
            borough=listing["borough"],
            distance_km=round(dist_km, 2),
            score=round(score, 4),
            picture_url=listing.get("picture_url"),
            listing_url=listing.get("listing_url"),
        ))

    # Sort by score descending
    comps.sort(key=lambda c: -c.score)

    # If too few comps, relax filters and try again
    if len(comps) < 3:
        comps = [c for c in _find_comps_relaxed(lat, lng, k) if c.listing_id not in exclude_ids]

    return comps[:settings.MAX_COMPS]


def _find_comps_relaxed(lat: float, lng: float, k: int) -> list[Comp]:
    """Find comps with relaxed filters (fallback). Returns empty if no good matches."""
    query = np.radians([[lat, lng]])
    distances, indices = _tree.query(query, k=min(k, len(_listings)))

    distances_km = distances[0] * 6371
    indices = indices[0]
    comps = []
    for dist_km, idx in zip(distances_km, indices):
        listing = _listings[idx]
        # At minimum: same room type
        if listing["room_type"] != "Entire home/apt":
            continue
        # At minimum: within 5km
        if dist_km > 5:
            continue
        score = max(0, 1 - dist_km / 10) * 0.5  # Lower score for relaxed matches

        comps.append(Comp(
            listing_id=listing["id"],
            lat=listing["lat"],
            lng=listing["lng"],
            bedrooms=listing["bedrooms"],
            bathrooms=listing["bathrooms"],
            accommodates=listing["accommodates"],
            room_type=listing["room_type"],
            price=listing["price"],
            revenue=listing["revenue"],
            borough=listing["borough"],
            distance_km=round(dist_km, 2),
            score=round(score, 4),
            picture_url=listing.get("picture_url"),
            listing_url=listing.get("listing_url"),
        ))

    return comps


def _score_comp(listing: dict, dist_km: float, target_bedrooms: int, target_bathrooms: int, target_accommodates: int) -> float:
    """Score a comparable listing."""
    distance_score = max(0, 1 - dist_km / 10) * 0.40
    bed_diff = abs(listing["bedrooms"] - target_bedrooms)
    bedroom_score = (1 - bed_diff / max(target_bedrooms, 1)) * 0.25
    bath_diff = abs(listing["bathrooms"] - target_bathrooms)
    bath_score = max(0, 1 - bath_diff / max(target_bathrooms, 1)) * 0.15
    cap_diff = abs(listing["accommodates"] - target_accommodates)
    capacity_score = (1 - cap_diff / max(target_accommodates, 1)) * 0.15
    type_score = 0.05
    # Distance/bedroom/capacity terms are individually non-negative by
    # construction (max(0, ...) or filtered to a bounded range upstream), so
    # clamping the total at 0 keeps every comp usable as a non-negative
    # weight in predict_from_comps()'s weighted average — a negative weight
    # there would let the "average" fall outside the range of the comps'
    # own revenues, which is not a valid weighted average.
    return max(0.0, distance_score + bedroom_score + bath_score + capacity_score + type_score)


def predict_from_comps(comps: list[Comp]) -> tuple[float | None, float]:
    """Predict revenue from comps. Returns (prediction, cv)."""
    if not comps:
        return None, 1.0

    revenues = [c.revenue for c in comps]
    weights = [c.score for c in comps]

    weighted_avg = np.average(revenues, weights=weights)
    mean_rev = np.mean(revenues)
    cv = np.std(revenues) / mean_rev if mean_rev > 0 else 1.0

    return weighted_avg, cv


# Pre-computed market stats cache
_market_stats_cache: dict[str, dict] = {}


def _precompute_market_stats(train_df: pd.DataFrame):
    """Pre-compute market stats per borough at startup (avoids repeated filtering)."""
    global _market_stats_cache
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    for borough in boroughs:
        col = f"borough_{borough}"
        if col in train_df.columns:
            subset = train_df[train_df[col] == 1]
        else:
            subset = train_df
        if len(subset) > 0:
            _market_stats_cache[borough] = {
                "borough": borough,
                "median_revenue": round(float(subset["revenue"].median()), 0),
                "median_price": round(float(subset["price_num"].median()), 0),
                "active_listings": len(subset),
            }
    logger.info(f"Pre-computed market stats for {len(_market_stats_cache)} boroughs")


def get_market_stats(borough: str) -> dict:
    """Get market statistics for a borough (uses pre-computed cache, refreshed
    automatically when the underlying training data changes on disk)."""
    _ensure_fresh()
    if borough in _market_stats_cache:
        return _market_stats_cache[borough]
    # Fallback: compute on the fly
    if _train_data is None:
        return {}
    return {
        "borough": borough,
        "median_revenue": round(float(_train_data["revenue"].median()), 0),
        "median_price": round(float(_train_data["price_num"].median()), 0),
        "active_listings": len(_train_data),
    }
