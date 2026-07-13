"""FastAPI application — AIRWORTHY API."""
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import secrets

import numpy as np
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from .schemas import (
    EstimateRequest, EstimateResponse, ErrorResponse,
    ConfidenceResponse, CompResponse, MarketResponse, ParcelResponse,
    HealthResponse, ModelInfoResponse, CreditsResponse,
)
from .exceptions import (
    GeocodingError, OutsideCoverageError,
    ModelNotReadyError, InvalidInputError,
)
from .validation import validate_input, in_nyc_bounds
from .geocoder import geocode
from .realie_client import get_parcel
from .comp_finder import build_index, find_comps, predict_from_comps, get_market_stats
from .market_estimator import estimate_from_db, covered_markets, get_demand_curve
from .features import build_features, get_borough_from_coords
from .model import load_model, predict, get_model_info, get_feature_columns
from .confidence import compute_confidence
from .enrichment import (
    estimate_adr_occupancy, monthly_forecast, performance_drivers, confidence_reasons,
    amenity_multiplier, amenity_drivers,
)
from .scoring import compute_airworthy
from .amenity_calibration import warm_calibration

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map database connection
import sqlite3
MAP_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'db', 'airbnb.db'
)


def _get_map_db():
    """Return a connection to the map/listings database."""
    conn = sqlite3.connect(MAP_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup
    logger.info("Loading model...")
    load_model()

    logger.info("Building comp index...")
    train_df = pd.read_csv(settings.TRAIN_DATA_PATH)
    build_index(train_df, source_path=settings.TRAIN_DATA_PATH)

    logger.info("Warming amenity calibration cache...")
    warm_calibration()

    if not API_KEYS:
        if IS_PRODUCTION:
            logger.warning(
                "[PRODUCTION] No API_KEYS configured — /v1/estimate and /v1/batch will reject "
                "any request that isn't recognized as coming from this app's own browser pages. "
                "Set the API_KEYS secret (comma-separated) to issue keys to other callers."
            )
        else:
            logger.warning(
                "AUTH DISABLED (dev mode): no API_KEYS configured — /v1/estimate and /v1/batch "
                "accept unauthenticated requests from any caller. Set the API_KEYS secret "
                "(comma-separated) to require an X-API-Key header before exposing this publicly."
            )

    logger.info("Ready!")
    yield
    # Shutdown
    logger.info("Shutting down...")


# Rate limiting
#
# Limits are keyed off the authenticated *partner* API key when one is
# present, so each key gets its own budget instead of sharing an IP bucket
# with everyone else behind the same NAT/proxy. Requests with no partner key
# — same-origin browser traffic (which uses the low-privilege BROWSER_API_KEY
# or, in dev, no key at all) — fall back to per-IP limiting so one shared
# browser key can't collapse every visitor into a single bucket.
#
# verify_api_key stashes the resolved partner key on request.state.api_key;
# _rate_limit_key reads it here.
def _rate_limit_key(request: Request) -> str:
    api_key = getattr(request.state, "api_key", None)
    if api_key:
        return f"key:{api_key}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_rate_limit_key)

app = FastAPI(
    title="AIRWORTHY",
    description="Short-term rental earnings instrument — modeled revenue ranges, not falsely-precise numbers.",
    version=settings.VERSION,
    lifespan=lifespan,
)
app.state.limiter = limiter

# Auth
#
# Every call to /v1/estimate and /v1/batch must present a valid X-API-Key
# header — no exceptions, no anonymous exemption. Two kinds of keys:
#   - API_KEYS: secret, comma-separated partner/server keys (never shipped
#     to a browser).
#   - BROWSER_API_KEY: a single public, low-privilege key rendered into our
#     own HTML pages (visible in page source, same trust model as a Stripe
#     "publishable key" or a Google Maps browser key) so app.js/property.js/
#     compare.js can call the API from client-side JS. It grants no more
#     access than any other valid key and is not a bypass of the header
#     requirement — it just answers "which key does the web UI itself use".
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
IS_PRODUCTION = bool(os.getenv("REPLIT_DEPLOYMENT"))

# Per-key rate-limit budgets.
#
# By default every authenticated partner key gets DEFAULT_ESTIMATE_LIMIT /
# DEFAULT_BATCH_LIMIT (and un-keyed browser/dev traffic is limited per-IP at
# the same rate). Any key can be given a bespoke budget via the
# API_KEY_RATE_LIMITS / API_KEY_BATCH_RATE_LIMITS secrets, each a
# comma-separated list of "<key>=<limit>" pairs where <limit> is any
# slowapi/limits string, e.g. "60/minute" or "1000/hour":
#
#   API_KEY_RATE_LIMITS="partnerA=120/minute,partnerB=10/minute"
#
# A key not listed falls back to the default. This lets us throttle a single
# noisy or leaked key without touching anyone else's budget.
DEFAULT_ESTIMATE_LIMIT = os.getenv("RATE_LIMIT_ESTIMATE", "30/minute")
DEFAULT_BATCH_LIMIT = os.getenv("RATE_LIMIT_BATCH", "5/minute")


def _parse_key_limits(env_value: str) -> dict[str, str]:
    """Parse "<key>=<limit>,<key>=<limit>" into {key: limit}."""
    out: dict[str, str] = {}
    for part in env_value.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, limit = part.split("=", 1)
        key, limit = key.strip(), limit.strip()
        if key and limit:
            out[key] = limit
    return out


API_KEY_RATE_LIMITS = _parse_key_limits(os.getenv("API_KEY_RATE_LIMITS", ""))
API_KEY_BATCH_RATE_LIMITS = _parse_key_limits(os.getenv("API_KEY_BATCH_RATE_LIMITS", ""))


def _limit_for(rate_limit_key: str, budgets: dict[str, str], default: str) -> str:
    """Resolve the rate-limit string for a resolved rate-limit key.

    _rate_limit_key tags authenticated partner keys as "key:<api_key>" and
    everything else (browser/dev traffic) as "ip:<addr>". Only real partner
    keys can carry a bespoke per-key budget; IP-bucketed traffic always uses
    the default.
    """
    if rate_limit_key.startswith("key:"):
        return budgets.get(rate_limit_key[len("key:"):], default)
    return default


# NB: slowapi only passes the resolved rate-limit key to a dynamic limit
# provider when its parameter is literally named "key" (it inspects the
# signature for that name), so do not rename this argument.
def _estimate_limit(key: str) -> str:
    return _limit_for(key, API_KEY_RATE_LIMITS, DEFAULT_ESTIMATE_LIMIT)


def _batch_limit(key: str) -> str:
    return _limit_for(key, API_KEY_BATCH_RATE_LIMITS, DEFAULT_BATCH_LIMIT)

BROWSER_API_KEY = os.getenv("BROWSER_API_KEY")
if not BROWSER_API_KEY:
    # No explicit browser key configured — mint one for this process so the
    # web UI keeps working; it's re-rendered into every page load, so an
    # ephemeral value (not surviving a restart) is fine.
    BROWSER_API_KEY = secrets.token_hex(16)


async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """Require a valid X-API-Key on every call.

    - Matches a configured partner key (API_KEYS) or the public browser key
      (BROWSER_API_KEY) -> allowed.
    - No API_KEYS configured at all and not in production -> allowed with no
      key (local dev, matches the project's pre-existing dev-mode behavior).
    - Anything else (missing, unknown, or wrong key; or unconfigured in
      production) -> rejected. There is no same-origin/cookie/header-based
      exemption — those are all spoofable by a plain script.

    Side effect: records the *partner* key on request.state.api_key so the
    rate limiter can give each key its own budget. The shared public
    BROWSER_API_KEY is deliberately NOT recorded — browser traffic must be
    limited per-IP (each visitor), not lumped into one bucket keyed off the
    single browser key.
    """
    if api_key and (api_key in API_KEYS or api_key == BROWSER_API_KEY):
        request.state.api_key = api_key if api_key in API_KEYS else None
        return api_key

    if not API_KEYS and not IS_PRODUCTION:
        request.state.api_key = None  # local dev, no keys configured at all
        return None

    raise HTTPException(status_code=401, detail="Missing or invalid API key")

# Static files and templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# --- Exception handlers ---

@app.exception_handler(GeocodingError)
async def geocoding_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "error": "geocoding_failed",
        "detail": str(exc),
        "suggestion": "Try a more specific address (e.g., '350 5th Ave, New York, NY 10118')",
    })

@app.exception_handler(OutsideCoverageError)
async def coverage_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "error": "outside_coverage_area",
        "detail": str(exc),
        "suggestion": "Try an address in a covered market. The detail lists which markets have data.",
    })

@app.exception_handler(InvalidInputError)
async def invalid_input_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "error": "invalid_input",
        "detail": str(exc),
    })

@app.exception_handler(Exception)
async def generic_handler(request, exc):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={
        "error": "internal_error",
        "detail": "An unexpected error occurred.",
    })


# --- Routes ---

@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'favicon.svg'
    )
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    # A 204 must have an empty body — JSONResponse(content=None) serializes
    # the string "null" as the body, which is inconsistent with the status.
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the web UI."""
    return templates.TemplateResponse(request=request, name="index.html",
                                       context={"browser_api_key": BROWSER_API_KEY})


@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    """Serve the map explorer."""
    return templates.TemplateResponse(request=request, name="map.html",
                                       context={"browser_api_key": BROWSER_API_KEY})


@app.get("/property", response_class=HTMLResponse)
async def property_report(request: Request):
    """Serve the property earnings report.

    Property facts (address, bedrooms, bathrooms, accommodates, nightly_rate)
    arrive as query params from the homepage's "View complete estimate" link
    or the map's "Open estimate" link — the page itself is static; all data
    fetching/rendering happens client-side against /v1/estimate.
    """
    return templates.TemplateResponse(request=request, name="property.html",
                                       context={"browser_api_key": BROWSER_API_KEY})


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    """Serve the property comparison screen.

    Initial property facts (address, bedrooms, bathrooms, accommodates,
    nightly_rate) arrive as query params from the homepage's or property
    report's "Compare" action — the page itself is static; the initial
    property plus any manually-added or saved properties are estimated
    client-side against /v1/estimate, one request per property.
    """
    return templates.TemplateResponse(request=request, name="compare.html",
                                       context={"browser_api_key": BROWSER_API_KEY})


@app.get("/api/cities")
async def cities(state: str | None = None):
    """Return available cities with counts and bounding boxes."""
    if not os.path.exists(MAP_DB_PATH):
        return {"cities": []}
    conn = _get_map_db()
    try:
        # Mirror /api/listings' "latest snapshot per city" semantics so chip
        # counts and bounds match what the map actually displays — otherwise
        # a city with multiple historical snapshots would show an inflated
        # count here versus the listings the map renders.
        sql = """
            SELECT state, city,
                   COUNT(*) as cnt,
                   MIN(latitude)  as min_lat,
                   MAX(latitude)  as max_lat,
                   MIN(longitude) as min_lng,
                   MAX(longitude) as max_lng
            FROM listings
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
              AND (state, city, snapshot_date) IN (
                  SELECT state, city, MAX(snapshot_date)
                  FROM listings
                  GROUP BY state, city
              )
        """
        params = []
        if state:
            sql += " AND state = ?"
            params.append(state)
        sql += " GROUP BY state, city ORDER BY cnt DESC"
        rows = conn.execute(sql, params).fetchall()
        cities_out = []
        for r in rows:
            cities_out.append({
                "state": r[0],
                "slug":  r[1],
                "count": r[2],
                "bounds": [[r[3], r[4]], [r[5], r[6]]],  # [[min_lat,max_lat],[min_lng,max_lng]]
            })
        # Real data freshness = latest snapshot date across the returned scope,
        # so the UI can show an accurate date instead of a hardcoded string.
        fresh_sql = "SELECT MAX(snapshot_date) FROM listings"
        fresh_params = []
        if state:
            fresh_sql += " WHERE state = ?"
            fresh_params.append(state)
        freshness = conn.execute(fresh_sql, fresh_params).fetchone()[0]
        return {"cities": cities_out, "data_freshness": freshness}
    finally:
        conn.close()


@app.get("/api/listings")
async def listings(
    north: float,
    south: float,
    east: float,
    west: float,
    limit: int = 1000,
    state: str | None = None,
    city: str | None = None,
    room_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    guest_favorites: bool = False,
    instant_book: bool = False,
):
    """Return listings within a bounding box for the map."""
    if not os.path.exists(MAP_DB_PATH):
        return {"listings": []}

    # Validate and clamp inputs
    if not (-90 <= south <= north <= 90) or not (-180 <= west <= east <= 180):
        return JSONResponse(status_code=400, content={"error": "invalid_bounds"})
    limit = max(1, min(limit, 5000))
    if min_price is not None and min_price < 0:
        return JSONResponse(status_code=400, content={"error": "min_price_must_be_non_negative"})
    if max_price is not None and max_price < 0:
        return JSONResponse(status_code=400, content={"error": "max_price_must_be_non_negative"})
    if min_price is not None and max_price is not None and min_price > max_price:
        return JSONResponse(status_code=400, content={"error": "min_price_cannot_exceed_max_price"})

    conn = _get_map_db()
    try:
        # Only show the latest snapshot per city to avoid duplicates when multiple snapshots exist.
        sql = """
            SELECT id, state, city, snapshot_date, name, room_type, bedrooms,
                   bathrooms, accommodates, price_numeric, number_of_reviews,
                   estimated_revenue_l365d, latitude, longitude, demand_curve
            FROM listings
            WHERE (state, city, snapshot_date) IN (
                SELECT state, city, MAX(snapshot_date)
                FROM listings
                GROUP BY state, city
            )
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
        """
        params = [south, north, west, east]

        if state:
            sql += " AND state = ?"
            params.append(state)
        if city:
            sql += " AND city = ?"
            params.append(city)
        if room_type:
            sql += " AND room_type = ?"
            params.append(room_type)
        if min_price is not None:
            sql += " AND price_numeric >= ?"
            params.append(min_price)
        if max_price is not None:
            sql += " AND price_numeric <= ?"
            params.append(max_price)
        if guest_favorites:
            sql += " AND review_scores_rating >= 4.8 AND number_of_reviews >= 10"
        if instant_book:
            sql += " AND instant_bookable = 1"

        sql += " ORDER BY estimated_revenue_l365d DESC NULLS LAST LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return {"listings": [dict(r) for r in rows]}
    finally:
        conn.close()


async def _do_estimate(req: EstimateRequest) -> EstimateResponse:
    """Core estimate logic shared by the route and the batch endpoint.

    Raises typed exceptions (GeocodingError / OutsideCoverageError /
    InvalidInputError) so both callers can translate them consistently — the
    route via FastAPI's exception handlers, batch via per-item error objects.
    """
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    # 1. Validate input
    validate_input(req.address, req.bedrooms, req.bathrooms, req.accommodates, req.nightly_rate)

    # 2. Geocode
    t0 = time.time()
    geo = geocode(req.address)
    geocode_ms = int((time.time() - t0) * 1000)

    # 2b. Real parcel/assessor enrichment (Realie). Optional and fail-open:
    #     never blocks or fails the estimate if unconfigured or unavailable.
    try:
        parcel = get_parcel(geo.lat, geo.lng)
    except Exception as e:
        logger.warning(f"[{request_id}] parcel enrichment failed: {e}")
        parcel = None

    # 3. Route by coverage: NYC uses the trained ML model; every other market
    #    is served by the comp-based estimate over the shared listings DB.
    if in_nyc_bounds(geo.lat, geo.lng):
        return _estimate_nyc_ml(req, geo, request_id, start, geocode_ms, parcel)
    return _estimate_from_market(req, geo, request_id, start, geocode_ms, parcel)


def _parcel_response(parcel) -> ParcelResponse | None:
    return ParcelResponse(**vars(parcel)) if parcel else None


def _estimate_nyc_ml(req: EstimateRequest, geo, request_id: str, start: float, geocode_ms: int, parcel=None) -> EstimateResponse:
    """NYC estimate using the trained LightGBM model + NYC comp index."""
    # 4. Find comps
    t0 = time.time()
    comps = find_comps(
        geo.lat, geo.lng, req.bedrooms, req.accommodates, req.bathrooms,
        exclude_ids=set(req.exclude_comp_ids) if req.exclude_comp_ids else None,
    )
    comp_ms = int((time.time() - t0) * 1000)

    # 5. Comp-based prediction
    comp_pred, comp_cv = predict_from_comps(comps)

    # 6. Determine borough
    borough = get_borough_from_coords(geo.lat, geo.lng)

    # 7. Build features
    feature_cols = get_feature_columns()
    features = build_features(
        req.nightly_rate, req.bedrooms, req.bathrooms, req.accommodates,
        geo.lat, geo.lng, comps, borough, feature_cols,
        minimum_nights=req.minimum_nights,
        is_superhost=req.is_superhost,
        host_listings_count=req.host_listings_count,
    )

    # 8. Model prediction
    t0 = time.time()
    log_revenue = predict(features)
    model_ms = int((time.time() - t0) * 1000)

    # 8b. Market stats (needed for fallback below)
    market = get_market_stats(borough)

    # 9. Smart blend: use comps when model is clearly wrong
    # Model is trained on existing listings. For new listings (no reviews),
    # it under-predicts. Comp-based prediction uses actual revenue from
    # similar properties, so it's more reliable for new listings.
    comp_revenue = float(comp_pred) if comp_pred is not None else None
    model_revenue = float(np.expm1(log_revenue))

    if comp_revenue is not None and comp_revenue > 0 and len(comps) >= 3:
        comp_median = np.median([c.revenue for c in comps])
        ratio = model_revenue / comp_median if comp_median > 0 else 1.0

        if 0.5 <= ratio <= 2.0:
            alpha = 0.7
        elif 0.25 <= ratio <= 4.0:
            alpha = 0.5
        else:
            alpha = 0.3

        final_log_revenue = alpha * log_revenue + (1 - alpha) * np.log1p(comp_revenue)
    elif comp_revenue is not None and comp_revenue > 0:
        # Few comps but some — blend heavily toward comps
        final_log_revenue = 0.3 * log_revenue + 0.7 * np.log1p(comp_revenue)
    else:
        # No comps at all — use market median instead of raw model
        market_revenue = market.get("median_revenue", 79130)
        final_log_revenue = 0.5 * log_revenue + 0.5 * np.log1p(market_revenue)

    annual_revenue = float(np.expm1(final_log_revenue))

    # 9b. Apply property-facts amenity adjustment (facts editor) — a modest,
    # disclosed uplift, applied after the model/comp blend so drivers below
    # can report its dollar impact against the pre-amenity figure.
    pre_amenity_revenue = annual_revenue
    annual_revenue = annual_revenue * amenity_multiplier(req.amenities, market_state="ny")

    # 10. Confidence
    comp_revenues = [c.revenue for c in comps]
    confidence = compute_confidence(annual_revenue, comp_revenues, len(comps))

    total_ms = int((time.time() - start) * 1000)
    logger.info(
        f"[{request_id}] address={req.address!r} lat={geo.lat:.4f} lng={geo.lng:.4f} "
        f"comps={len(comps)} revenue=${annual_revenue:,.0f} conf={confidence.level} "
        f"geocode={geocode_ms}ms comp={comp_ms}ms model={model_ms}ms total={total_ms}ms"
    )

    # 11. Derived metrics, forecast, drivers, and confidence reasons
    adr, occupancy = estimate_adr_occupancy(annual_revenue, req.nightly_rate)
    avg_distance_km = sum(c.distance_km for c in comps) / len(comps) if comps else 0.0
    bed_matches = sum(1 for c in comps if c.bedrooms == req.bedrooms)
    bedroom_match_ratio = bed_matches / len(comps) if comps else 0.0
    drivers = performance_drivers(
        nightly_rate=req.nightly_rate,
        bedrooms=req.bedrooms,
        median_price=market.get("median_price", 0),
        n_comps=len(comps),
        is_superhost=req.is_superhost,
        avg_distance_km=avg_distance_km,
    )
    drivers = drivers + amenity_drivers(req.amenities, pre_amenity_revenue, market_state="ny")
    reasons, weaknesses = confidence_reasons(
        n_comps=len(comps),
        avg_distance_km=avg_distance_km,
        cv=confidence.cv,
        data_freshness=settings.DATA_FRESHNESS,
        bedroom_match_ratio=bedroom_match_ratio,
    )

    # 11b. AIRWORTHY verdict/score — same transparent read used by the
    # comp-based market path, benchmarked against this borough's median
    # revenue.
    airworthy = compute_airworthy(
        annual_revenue=annual_revenue,
        benchmark_revenue=market.get("median_revenue", 0),
        cv=confidence.cv,
        n_comps=len(comps),
    )

    # 11c. Seasonality curve — sourced from the shared listings DB, not this
    # NYC path's own comp index (see get_demand_curve docstring). NYC has no
    # rows in that DB, so this is expected to come back None there.
    demand_curve = None
    if os.path.exists(MAP_DB_PATH):
        dc_conn = _get_map_db()
        try:
            demand_curve = get_demand_curve(dc_conn, geo.lat, geo.lng, req.bedrooms, req.property_type)
        finally:
            dc_conn.close()

    # 12. Format response
    return EstimateResponse(
        address=req.address,
        lat=round(geo.lat, 6),
        lng=round(geo.lng, 6),
        annual_revenue=round(annual_revenue, 0),
        airworthy_score=airworthy.score,
        airworthy_verdict=airworthy.verdict,
        airworthy_reason=airworthy.reason,
        confidence=ConfidenceResponse(
            level=confidence.level,
            revenue_lower=confidence.revenue_lower,
            revenue_upper=confidence.revenue_upper,
            cv=confidence.cv,
            reasons=reasons,
            weaknesses=weaknesses,
        ),
        comps=[
            CompResponse(
                id=c.listing_id,
                distance_km=c.distance_km,
                bedrooms=c.bedrooms,
                revenue=round(c.revenue, 0),
                similarity_score=c.score,
                borough=c.borough,
                price=c.price,
                reason_included="same bedroom count" if c.bedrooms == req.bedrooms else "closest available match",
                differences=(
                    f"{abs(c.bedrooms - req.bedrooms)} {'more' if c.bedrooms > req.bedrooms else 'fewer'} bedroom(s)"
                    if c.bedrooms != req.bedrooms else "closely matches this property"
                ),
            )
            for c in comps[:20]
        ],
        market=MarketResponse(
            borough=market.get("borough", borough),
            median_revenue=market.get("median_revenue", 0),
            median_price=market.get("median_price", 0),
            active_listings=market.get("active_listings", 0),
            adr=adr,
            occupancy_rate=occupancy,
        ),
        monthly_forecast=monthly_forecast(annual_revenue, confidence.cv),
        performance_drivers=drivers,
        demand_curve=demand_curve,
        parcel=_parcel_response(parcel),
        disclaimer=settings.DISCLAIMER,
        data_source=settings.DATA_SOURCE,
        model_version=get_model_info().get("version", settings.VERSION),
        data_freshness=settings.DATA_FRESHNESS,
    )


def _estimate_from_market(req: EstimateRequest, geo, request_id: str, start: float, geocode_ms: int, parcel=None) -> EstimateResponse:
    """Comp-based estimate for any market present in the listings DB.

    Raises OutsideCoverageError (with a data-driven message) when there aren't
    enough nearby comps — so unsupported areas fail honestly instead of
    returning a bogus number.
    """
    if not os.path.exists(MAP_DB_PATH):
        raise OutsideCoverageError("Market data is not available.")

    conn = _get_map_db()
    try:
        result = estimate_from_db(
            conn, geo.lat, geo.lng, req.bedrooms, req.accommodates, req.property_type,
            nightly_rate=req.nightly_rate,
            is_superhost=req.is_superhost,
            exclude_ids=set(req.exclude_comp_ids) if req.exclude_comp_ids else None,
            amenities=req.amenities,
        )
        markets = covered_markets(conn)
        demand_curve = get_demand_curve(conn, geo.lat, geo.lng, req.bedrooms, req.property_type) if result else None
    finally:
        conn.close()

    if result is None:
        covered = ", ".join(markets) if markets else "none yet"
        raise OutsideCoverageError(
            f"No market data near this address yet. Covered markets: {covered}."
        )

    total_ms = int((time.time() - start) * 1000)
    logger.info(
        f"[{request_id}] address={req.address!r} lat={geo.lat:.4f} lng={geo.lng:.4f} "
        f"comps={result['n_comps']} revenue=${result['annual_revenue']:,.0f} "
        f"conf={result['confidence']['level']} source=comps "
        f"geocode={geocode_ms}ms total={total_ms}ms"
    )

    return EstimateResponse(
        address=req.address,
        lat=round(geo.lat, 6),
        lng=round(geo.lng, 6),
        annual_revenue=result["annual_revenue"],
        airworthy_score=result["airworthy_score"],
        airworthy_verdict=result["airworthy_verdict"],
        airworthy_reason=result["airworthy_reason"],
        confidence=ConfidenceResponse(**result["confidence"]),
        comps=[CompResponse(**c) for c in result["comps"]],
        market=MarketResponse(**result["market"]),
        monthly_forecast=result.get("monthly_forecast", []),
        performance_drivers=result.get("performance_drivers", []),
        demand_curve=demand_curve,
        parcel=_parcel_response(parcel),
        disclaimer=settings.DISCLAIMER,
        data_source=settings.DATA_SOURCE,
        model_version="comps-1.0",
        data_freshness=result["data_freshness"] or settings.DATA_FRESHNESS,
    )


@app.post("/v1/estimate", response_model=EstimateResponse)
@limiter.limit(_estimate_limit)
async def estimate(request: Request, req: EstimateRequest, api_key: str = Depends(verify_api_key)):
    """Single property revenue estimate."""
    return await _do_estimate(req)


# Typed errors → stable per-item error codes for the batch response.
_BATCH_ERROR_CODES = {
    GeocodingError: "geocoding_failed",
    OutsideCoverageError: "outside_coverage_area",
    InvalidInputError: "invalid_input",
}


@app.post("/v1/batch")
@limiter.limit(_batch_limit)
async def batch_estimate(request: Request, requests: list[EstimateRequest], api_key: str = Depends(verify_api_key)):
    """Batch estimates (max 20)."""
    if len(requests) > settings.MAX_BATCH:
        return JSONResponse(status_code=413, content={
            "error": "batch_too_large",
            "detail": f"Maximum batch size is {settings.MAX_BATCH}",
        })

    results = []
    for req_item in requests:
        try:
            result = await _do_estimate(req_item)
            results.append(result.model_dump())
        except (GeocodingError, OutsideCoverageError, InvalidInputError) as e:
            # Preserve the specific reason instead of collapsing to a generic error.
            code = _BATCH_ERROR_CODES.get(type(e), "estimation_failed")
            results.append({"error": code, "detail": str(e)})
        except Exception as e:
            logger.exception(f"Batch item failed: {e}")
            results.append({"error": "estimation_failed", "detail": "Could not estimate this property"})

    return results


@app.get("/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.get("/v1/ready")
async def ready():
    from .model import _model as m
    from .comp_finder import _tree as t
    return {"model_loaded": m is not None, "index_loaded": t is not None}


@app.get("/v1/model/info", response_model=ModelInfoResponse)
async def model_info():
    info = get_model_info()
    return ModelInfoResponse(**info)


@app.get("/v1/credits", response_model=CreditsResponse)
async def credits():
    return CreditsResponse(
        data_source="InsideAirbnb",
        license="CC BY 4.0",
        license_url=settings.LICENSE_URL,
        attribution="Data from InsideAirbnb (insideairbnb.com), licensed under CC BY 4.0. "
                    "Data has been processed and transformed for revenue estimation purposes.",
    )
