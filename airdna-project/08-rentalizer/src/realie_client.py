"""Real parcel/assessor data enrichment via the Realie Property Data API
(https://docs.realie.ai). THREAD-SAFE.

This is additive, optional enrichment: it never blocks or fails the revenue
estimate. If the API key is missing, the request errors, times out, or no
parcel is found, `get_parcel` returns None and callers proceed unaffected —
mirroring the fail-open pattern in geocoder.py.
"""
import logging
import math
import threading
from dataclasses import dataclass

from cachetools import TTLCache

from .config import settings

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
# Assessor/parcel records change rarely (annual reassessment cycles), so cache
# far longer than geocoding results.
_cache = TTLCache(maxsize=5000, ttl=30 * 24 * 3600)

_session = None
_session_lock = threading.Lock()


def _get_session():
    """Get or create requests session (singleton)."""
    global _session
    with _session_lock:
        if _session is None:
            import requests
            _session = requests.Session()
    return _session


@dataclass
class ParcelData:
    """A subset of Realie's property record relevant to a rental investment report."""
    parcel_id: str | None = None
    year_built: int | None = None
    lot_acres: float | None = None
    building_area_sqft: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    stories: float | None = None
    has_garage: bool | None = None
    has_pool: bool | None = None
    construction_type: str | None = None
    roof_type: str | None = None
    owner_name: str | None = None
    assessed_market_value: float | None = None
    avm_value: float | None = None
    avm_value_low: float | None = None
    avm_value_high: float | None = None
    last_sale_price: float | None = None
    last_sale_date: str | None = None
    source: str = "realie"


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 3958.8  # Earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_parcel(lat: float, lng: float) -> ParcelData | None:
    """Look up the parcel at (lat, lng). Never raises; returns None on any failure."""
    if not settings.REALIE_API_KEY:
        return None

    key = (round(lat, 5), round(lng, 5))
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    try:
        result = _fetch_parcel(lat, lng)
    except Exception as e:
        logger.warning(f"Realie parcel lookup failed for ({lat}, {lng}): {e}")
        return None

    with _cache_lock:
        _cache[key] = result
    return result


def _fetch_parcel(lat: float, lng: float) -> ParcelData | None:
    session = _get_session()
    url = f"{settings.REALIE_BASE_URL}/public/property/location/"
    params = {
        "latitude": lat,
        "longitude": lng,
        # 0.1mi (~500ft): tight enough to stay on the target parcel, but wide
        # enough to absorb geocoding imprecision and parcel-centroid offset —
        # radii below ~0.05mi frequently return zero results even directly
        # over a real parcel (verified against the live API).
        "radius": 0.1,
        "limit": 5,
        "residential": True,
    }
    headers = {"Authorization": settings.REALIE_API_KEY}

    resp = session.get(url, params=params, headers=headers, timeout=settings.REALIE_TIMEOUT)

    if resp.status_code == 401:
        logger.warning("Realie API key rejected (401 Unauthorized) — check REALIE_API_KEY")
        return None
    if resp.status_code == 403:
        logger.warning("Realie usage limit exceeded (403 Forbidden)")
        return None
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    data = resp.json()
    properties = data.get("properties") or []
    if not properties:
        return None

    best = _closest_property(properties, lat, lng)
    if best is None:
        return None
    return _parse_property(best)


def _closest_property(properties: list[dict], lat: float, lng: float) -> dict | None:
    """Location search returns candidates within a radius, not sorted by
    distance — pick the one nearest the exact geocoded point."""
    best_prop, best_dist = None, float("inf")
    for p in properties:
        coords = (p.get("location") or {}).get("coordinates")
        if not coords or len(coords) != 2:
            continue
        p_lng, p_lat = coords
        dist = _haversine_miles(lat, lng, p_lat, p_lng)
        if dist < best_dist:
            best_prop, best_dist = p, dist
    return best_prop if best_prop is not None else (properties[0] if properties else None)


def _parse_property(p: dict) -> ParcelData:
    return ParcelData(
        parcel_id=p.get("parcelId"),
        year_built=p.get("yearBuilt"),
        lot_acres=p.get("acres"),
        building_area_sqft=p.get("buildingArea"),
        bedrooms=p.get("totalBedrooms"),
        bathrooms=p.get("totalBathrooms"),
        stories=p.get("stories"),
        has_garage=p.get("garage"),
        has_pool=p.get("pool"),
        construction_type=p.get("constructionType"),
        roof_type=p.get("roofType"),
        owner_name=p.get("ownerName"),
        assessed_market_value=p.get("totalMarketValue"),
        avm_value=p.get("modelValue"),
        avm_value_low=p.get("modelValueMin"),
        avm_value_high=p.get("modelValueMax"),
        last_sale_price=p.get("transferPrice"),
        last_sale_date=p.get("transferDate"),
    )
