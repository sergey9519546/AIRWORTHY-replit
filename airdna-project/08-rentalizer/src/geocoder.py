"""Geocoding with Mapbox primary, Nominatim fallback, listings-DB fallback, and caching. THREAD-SAFE."""
import logging
import os
import sqlite3
import threading
import urllib.parse
from dataclasses import dataclass
from cachetools import TTLCache
from geopy.geocoders import Nominatim

from .config import settings
from .exceptions import GeocodingError

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
_cache = TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)

_geolocator = None
_geolocator_lock = threading.Lock()

_session = None
_session_lock = threading.Lock()


def _db_path() -> str:
    """Path to the shared Airbnb/listings SQLite database."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "db", "airbnb.db",
    )


def _get_geolocator():
    """Get or create Nominatim instance (singleton)."""
    global _geolocator
    with _geolocator_lock:
        if _geolocator is None:
            _geolocator = Nominatim(user_agent="rentalizer-v1", timeout=10)
    return _geolocator


def _get_session():
    """Get or create requests session (singleton)."""
    global _session
    with _session_lock:
        if _session is None:
            import requests
            _session = requests.Session()
    return _session


@dataclass
class GeocodeResult:
    lat: float
    lng: float
    display_name: str
    source: str


def normalize_address(address: str) -> str:
    return address.strip().lower()


def geocode(address: str) -> GeocodeResult:
    """Geocode an address. Thread-safe with caching."""
    key = normalize_address(address)

    # Check cache (thread-safe)
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    # Try Mapbox
    if settings.MAPBOX_TOKEN:
        try:
            result = _geocode_mapbox(address)
            if result:
                with _cache_lock:
                    _cache[key] = result
                return result
        except Exception as e:
            logger.warning(f"Mapbox failed: {e}")

    # Fallback to Nominatim
    try:
        result = _geocode_nominatim(address)
        if result:
            with _cache_lock:
                _cache[key] = result
            return result
    except Exception as e:
        logger.warning(f"Nominatim failed: {e}")

    # Fallback to local listings database by name (e.g., an Airbnb listing title
    # that a user pasted into the address box). A per-connection handle keeps the
    # geocoder thread-safe even though SQLite connections must not cross threads.
    try:
        result = _geocode_listings_db(address)
        if result:
            with _cache_lock:
                _cache[key] = result
            return result
    except Exception as e:
        logger.warning(f"Listings DB geocode fallback failed: {e}")

    raise GeocodingError(f"Could not geocode: {address}")


def _geocode_listings_db(address: str) -> GeocodeResult | None:
    """Geocode using the local listings database by exact listing name.

    Many users paste the Airbnb listing title into the address box. When the
    external geocoders can't resolve that title, fall back to a case-insensitive
    exact match against the listings we already have. Each call opens its own
    connection so the geocoder stays thread-safe.
    """
    db_path = _db_path()
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            normalized = normalize_address(address)
            row = conn.execute(
                """
                SELECT latitude, longitude, city, state, name
                FROM listings
                WHERE LOWER(name) = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            if not row:
                return None

            city = row["city"] or ""
            state = row["state"] or ""
            location = f"{city}, {state}".strip(", ")
            display = f"{row['name']} ({location})" if location else row["name"]
            return GeocodeResult(
                lat=row["latitude"],
                lng=row["longitude"],
                display_name=display,
                source="listings_db",
            )
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Listings DB geocode fallback failed: {e}")
        return None


def _geocode_mapbox(address: str) -> GeocodeResult | None:
    """Geocode using Mapbox API. URL-encodes address."""
    session = _get_session()
    encoded = urllib.parse.quote(address)
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"
    params = {
        "access_token": settings.MAPBOX_TOKEN,
        "country": "US",
        "types": "address",
        "limit": 1,
    }

    resp = session.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        return None

    feature = features[0]
    lng, lat = feature["center"]

    return GeocodeResult(
        lat=lat, lng=lng,
        display_name=feature.get("place_name", address),
        source="mapbox",
    )


def _geocode_nominatim(address: str) -> GeocodeResult | None:
    """Geocode using Nominatim (singleton)."""
    geolocator = _get_geolocator()
    location = geolocator.geocode(address, country_codes="us", limit=1)

    if not location:
        return None

    return GeocodeResult(
        lat=location.latitude, lng=location.longitude,
        display_name=location.address, source="nominatim",
    )
