"""Real property-photo enrichment via Firecrawl's search+scrape API
(https://docs.firecrawl.dev). THREAD-SAFE.

Given a resolved street address, this finds a real-estate listing for that
property and extracts a real photo URL, the source page URL, and the source
site name. It references the source image URL directly — it never downloads or
re-hosts image bytes.

Like realie_client, this is additive, optional enrichment: it NEVER blocks or
fails the revenue estimate. When the API key is missing, the request errors,
times out, rate-limits, or nothing is found, `get_property_photo` returns None
and callers proceed unaffected.
"""
import logging
import threading
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from cachetools import TTLCache

from .config import settings

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
# Listing photos for a given address change rarely; cache generously so repeat
# report views don't re-spend scrape credits. Negative (None) results are
# cached too, so an address with no findable photo isn't re-scraped every load.
_cache = TTLCache(maxsize=5000, ttl=7 * 24 * 3600)

_session = None
_session_lock = threading.Lock()

# Real-estate sites we prefer a photo from, in priority order. A result whose
# URL host contains one of these wins over a generic web result.
_PREFERRED_SITES = (
    "zillow.com", "redfin.com", "realtor.com", "trulia.com",
    "homes.com", "compass.com", "apartments.com",
)


def _get_session():
    global _session
    with _session_lock:
        if _session is None:
            import requests
            _session = requests.Session()
    return _session


@dataclass
class PropertyPhoto:
    """A real photo of a property plus where it came from."""
    photo_url: str
    source_url: str
    source_site: str


def _normalize(address: str) -> str:
    return " ".join((address or "").split()).strip().lower()


def get_property_photo(address: str) -> PropertyPhoto | None:
    """Find a real photo for `address`. Never raises; returns None on any
    failure (unconfigured, rate-limited, timeout, or nothing found)."""
    if not settings.FIRECRAWL_API_KEY:
        return None
    if not address or not address.strip():
        return None

    key = _normalize(address)
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    try:
        result = _fetch_photo(address)
    except Exception as e:
        logger.warning(f"Firecrawl photo lookup failed for {address!r}: {e}")
        # Do NOT cache transient errors — a later retry may succeed.
        return None

    with _cache_lock:
        _cache[key] = result
    return result


def _fetch_photo(address: str) -> PropertyPhoto | None:
    session = _get_session()
    url = f"{settings.FIRECRAWL_BASE_URL}/v1/search"
    payload = {
        "query": f"{address} home for sale real estate listing",
        # Kept small: each extra result means another page Firecrawl has to
        # scrape server-side, and this call sits directly in the estimate's
        # critical path (mitigated by the fail-open timeout above + caching).
        "limit": 3,
        # Scraping each result populates `metadata`, where og:image lives.
        "scrapeOptions": {"formats": ["markdown"]},
    }
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = session.post(url, json=payload, headers=headers, timeout=settings.FIRECRAWL_TIMEOUT)

    if resp.status_code in (401, 403):
        logger.warning(f"Firecrawl key rejected or over limit ({resp.status_code})")
        return None
    if resp.status_code == 429:
        logger.warning("Firecrawl rate limit hit (429)")
        return None
    resp.raise_for_status()

    body = resp.json()
    results = body.get("data") or []
    if not results:
        return None

    return _pick_photo(results)


def _pick_photo(results: list[dict]) -> PropertyPhoto | None:
    """Choose the best result carrying an image, preferring known real-estate
    sites over generic web pages."""
    best = None
    best_rank = len(_PREFERRED_SITES) + 1
    for item in results:
        page_url = item.get("url")
        image = _extract_image(item)
        if not page_url or not image:
            continue
        host = (urlparse(page_url).hostname or "").lower()
        rank = next(
            (i for i, site in enumerate(_PREFERRED_SITES) if site in host),
            len(_PREFERRED_SITES),
        )
        if rank < best_rank:
            best = PropertyPhoto(
                photo_url=image,
                source_url=page_url,
                source_site=_site_name(host),
            )
            best_rank = rank
            if rank == 0:
                break  # top-priority site — can't do better
    return best


# Filenames real-estate/search sites fall back to when there's no actual
# listing photo (a generic site icon or "no photography available" stock
# image) — these are technically valid image URLs but not real photos.
_PLACEHOLDER_MARKERS = (
    "missingphotography", "apple-touch-icon", "favicon", "placeholder",
    "no-photo", "nophoto", "default-image", "og-default",
)

# Some sites (notably Zillow) fall back to a static satellite/roadmap
# screenshot as their og:image when the specific listing has no real photos
# indexed. These are real, loadable images but not photos of the home, so
# they're treated the same as placeholders: skip and fall through to the
# next candidate image or search result.
_STATIC_MAP_MARKERS = (
    "maps.googleapis.com/maps/api/staticmap",
    "maps.google.com/maps/api/staticmap",
    "/staticmap", "staticmap?", "static-map",
    "maps.googleapis.com/maps/api/streetview",
    "tile.openstreetmap.org", "api.mapbox.com/styles",
)


def _extract_image(item: dict) -> str | None:
    """Pull an og:image (or equivalent) out of a Firecrawl scrape result."""
    meta = item.get("metadata") or {}
    page_url = item.get("url") or ""
    for key in ("ogImage", "og:image", "image", "twitter:image", "twitterImage"):
        val = meta.get(key)
        if isinstance(val, list):
            val = val[0] if val else None
        if not isinstance(val, str) or not val:
            continue
        # Firecrawl sometimes reports these as site-relative paths rather than
        # absolute URLs; resolve them against the page they came from.
        resolved = urljoin(page_url, val) if page_url else val
        if not resolved.startswith("http"):
            continue
        lowered = resolved.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
            continue
        if any(marker in lowered for marker in _STATIC_MAP_MARKERS):
            continue
        return resolved
    return None


def _site_name(host: str) -> str:
    """Human-readable source label, e.g. 'www.zillow.com' -> 'Zillow'."""
    host = host.lstrip("www.")
    base = host.split(".")[0] if host else host
    return base.capitalize() if base else host
