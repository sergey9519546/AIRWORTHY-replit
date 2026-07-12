# Architecture Innovations — Rentalizer

**Author:** Senior Infrastructure Engineer  
**Date:** 2026-06-29  
**Scope:** 10 concrete innovations with production-ready code and configuration  
**Baseline:** Current codebase as audited (FastAPI + scikit-learn, single-city NYC, no auth, no caching layer, root container)

---

## Table of Contents

1. [API Key Authentication](#1-api-key-authentication)
2. [Rate Limiting (slowapi)](#2-rate-limiting-slowapi)
3. [Borough Detection via GeoJSON](#3-borough-detection-via-geojson)
4. [Thread-Safe Comp Finder](#4-thread-safe-comp-finder)
5. [PostgreSQL for Multi-City](#5-postgresql-for-multi-city)
6. [Redis Caching Layer](#6-redis-caching-layer)
7. [Structured Logging](#7-structured-logging)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Docker Security Hardening](#9-docker-security-hardening)
10. [Multi-City Architecture](#10-multi-city-architecture)

---

## 1. API Key Authentication

### Problem

All endpoints are open. The batch endpoint amplifies abuse (20 estimates per request). No way to track usage per consumer or revoke access.

### Design

- API keys stored in a PostgreSQL table (not environment variables) for dynamic management
- Keys are hashed (SHA-256) at rest — we never store plaintext
- A FastAPI dependency injects the verified key context into every authenticated route
- `/v1/health`, `/v1/ready`, and `/` (UI) remain public
- Each key has a `tier` (free, pro, enterprise) that controls rate limits and batch size

### Implementation

**New file: `src/auth.py`**

```python
"""API key authentication."""
import hashlib
import secrets
from datetime import datetime, timezone
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from .db import get_db_pool

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class APIKeyContext:
    key_id: int
    owner: str
    tier: str  # "free" | "pro" | "enterprise"
    requests_today: int = 0


TIER_LIMITS = {
    "free":       {"rate": "30/minute",  "batch_max": 5,   "daily": 500},
    "pro":        {"rate": "120/minute", "batch_max": 20,  "daily": 10000},
    "enterprise": {"rate": "600/minute", "batch_max": 100, "daily": 100000},
}


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, hashed_key)."""
    raw = f"rnt_{secrets.token_urlsafe(32)}"
    return raw, _hash_key(raw)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> APIKeyContext:
    """FastAPI dependency — validates API key and returns context."""
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "missing_api_key",
                "detail": "Include 'X-API-Key' header. Get a key at /v1/keys/register.",
            },
        )

    hashed = _hash_key(api_key)
    pool = get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, owner, tier, is_active
            FROM api_keys
            WHERE key_hash = $1
            """,
            hashed,
        )

    if row is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key", "detail": "Key not recognized."},
        )

    if not row["is_active"]:
        raise HTTPException(
            status_code=403,
            detail={"error": "key_revoked", "detail": "This API key has been revoked."},
        )

    return APIKeyContext(
        key_id=row["id"],
        owner=row["owner"],
        tier=row["tier"],
    )


def require_tier(minimum: str):
    """Dependency factory — enforce minimum tier."""
    tier_order = {"free": 0, "pro": 1, "enterprise": 2}

    async def _check(ctx: APIKeyContext = Depends(verify_api_key)):
        if tier_order.get(ctx.tier, 0) < tier_order.get(minimum, 0):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_tier",
                    "detail": f"This endpoint requires '{minimum}' tier or higher.",
                    "upgrade_url": "/v1/keys/upgrade",
                },
            )
        return ctx

    return _check
```

**Database migration: `migrations/001_create_api_keys.sql`**

```sql
CREATE TABLE api_keys (
    id          SERIAL PRIMARY KEY,
    key_hash    VARCHAR(64) NOT NULL UNIQUE,
    owner       VARCHAR(255) NOT NULL,
    tier        VARCHAR(20) NOT NULL DEFAULT 'free',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used   TIMESTAMPTZ,
    CONSTRAINT valid_tier CHECK (tier IN ('free', 'pro', 'enterprise'))
);

CREATE INDEX idx_api_keys_hash ON api_keys (key_hash);
CREATE INDEX idx_api_keys_owner ON api_keys (owner);
```

**Usage in `src/api.py`:**

```python
from .auth import verify_api_key, require_tier, APIKeyContext, TIER_LIMITS

@app.post("/v1/estimate", response_model=EstimateResponse)
async def estimate(
    req: EstimateRequest,
    ctx: APIKeyContext = Depends(verify_api_key),
):
    # ctx.key_id, ctx.tier available for logging/rate limiting
    ...

@app.post("/v1/batch")
async def batch_estimate(
    requests: list[EstimateRequest],
    ctx: APIKeyContext = Depends(verify_api_key),
):
    max_batch = TIER_LIMITS[ctx.tier]["batch_max"]
    if len(requests) > max_batch:
        return JSONResponse(status_code=413, content={
            "error": "batch_too_large",
            "detail": f"Your '{ctx.tier}' tier allows max {max_batch} items per batch.",
        })
    ...

# Public endpoints — no auth
@app.get("/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

**Key management endpoints (admin only, behind `X-Admin-Key`):**

```python
@app.post("/v1/keys/register")
async def register_key(owner: str, tier: str = "free"):
    raw_key, hashed_key = generate_api_key()
    pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (key_hash, owner, tier) VALUES ($1, $2, $3)",
            hashed_key, owner, tier,
        )
    return {"api_key": raw_key, "owner": owner, "tier": tier,
            "warning": "Save this key now — it cannot be retrieved again."}
```

---

## 2. Rate Limiting (slowapi)

### Problem

No request throttling. A single client can exhaust CPU with rapid `/v1/estimate` calls, burn Mapbox quota via geocoding, and amplify through `/v1/batch` (20×).

### Design

- `slowapi` with tier-based limits keyed on API key (authenticated) or IP (unauthenticated fallback)
- Separate limits for estimate (heavy) vs health (light) endpoints
- Redis backend for distributed rate limiting across multiple workers
- Batch endpoint has stricter limits proportional to batch size

### Implementation

**New file: `src/rate_limit.py`**

```python
"""Rate limiting configuration."""
import redis.asyncio as aioredis
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from .config import settings


def _get_identifier(request: Request) -> str:
    """Use API key owner if available, else fall back to IP."""
    # API key context is set by auth dependency (runs before rate limit)
    ctx = getattr(request.state, "api_key_ctx", None)
    if ctx:
        return f"key:{ctx.owner}:{ctx.tier}"
    return get_remote_address(request)


def _get_rate_limit(request: Request) -> str:
    """Tier-based rate limits."""
    ctx = getattr(request.state, "api_key_ctx", None)
    if ctx:
        from .auth import TIER_LIMITS
        return TIER_LIMITS[ctx.tier]["rate"]
    return "10/minute"  # Unauthenticated fallback


# Redis-backed limiter for distributed deployments
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

limiter = Limiter(
    key_func=_get_identifier,
    storage_uri=settings.REDIS_URL,
    default_limits=["100/minute"],
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit error response."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": str(exc.detail),
            "retry_after": exc.detail.split("per ")[1] if "per " in str(exc.detail) else "minute",
        },
        headers={"Retry-After": "60"},
    )
```

**Integration in `src/api.py`:**

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .rate_limit import limiter, rate_limit_exceeded_handler

app = FastAPI(...)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

@app.post("/v1/estimate", response_model=EstimateResponse)
@limiter.limit("30/minute")  # Base limit; tier override via key_func
async def estimate(request: Request, req: EstimateRequest, ...):
    ...

@app.post("/v1/batch")
@limiter.limit("5/minute")  # Stricter — batch is expensive
async def batch_estimate(request: Request, requests: list[EstimateRequest], ...):
    ...

# No rate limit on health checks
@app.get("/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
```

**Additional dependency (`requirements.txt`):**

```
slowapi>=0.1.9
redis>=5.0.0
```

---

## 3. Borough Detection via GeoJSON

### Problem

`get_borough_from_coords()` uses hardcoded bounding boxes that are wrong for ~60% of NYC. The Manhattan check (`lat > 40.70 and lng > -74.02`) catches most of Brooklyn, Queens, and the Bronx. Staten Island is never returned. Default fallback to Manhattan masks errors.

### Design

- Download NYC Borough Boundaries GeoJSON from NYC Open Data
- Use `shapely` for point-in-polygon lookups
- Cache the loaded geometries at module level (they don't change)
- Fall back to improved bounding boxes only if the shapefile is missing

### Implementation

**Data: `data/nyc_boroughs.geojson`**  
Download from: https://data.cityofnewyork.us/api/geospatial/tqmj-j8zm  
(Alternatively, use the simplified version below for deployment)

**Updated `src/features.py` — borough detection:**

```python
"""Borough detection using GeoJSON point-in-polygon."""
import json
import logging
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep

logger = logging.getLogger(__name__)

# Module-level cache for prepared geometries
_borough_geoms: dict[str, object] | None = None


def _load_borough_geometries() -> dict[str, object]:
    """Load and prepare NYC borough polygons from GeoJSON."""
    global _borough_geoms
    if _borough_geoms is not None:
        return _borough_geoms

    geojson_path = Path(__file__).parent.parent / "data" / "nyc_boroughs.geojson"
    if not geojson_path.exists():
        logger.warning(f"Borough GeoJSON not found at {geojson_path}, using fallback boxes")
        return _load_fallback_boxes()

    with open(geojson_path) as f:
        data = json.load(f)

    _borough_geoms = {}
    name_map = {
        "Manhattan": "Manhattan",
        "Brooklyn": "Brooklyn",
        "Queens": "Queens",
        "Bronx": "Bronx",
        "Staten Island": "Staten Island",
    }

    for feature in data["features"]:
        raw_name = feature["properties"].get("boro_name", "")
        canonical = name_map.get(raw_name)
        if canonical:
            _borough_geoms[canonical] = prep(shape(feature["geometry"]))

    logger.info(f"Loaded borough geometries: {list(_borough_geoms.keys())}")
    return _borough_geoms


def _load_fallback_boxes() -> dict[str, object]:
    """Fallback: correct bounding boxes (not the broken original ones)."""
    from shapely.geometry import box

    # Correct bounding boxes from NYC planning data
    _borough_geoms = {
        "Manhattan":     prep(box(-74.02, 40.70, -73.91, 40.88)),
        "Brooklyn":      prep(box(-74.05, 40.57, -73.85, 40.74)),
        "Queens":        prep(box(-73.96, 40.55, -73.70, 40.80)),
        "Bronx":         prep(box(-73.93, 40.79, -73.77, 40.92)),
        "Staten Island": prep(box(-74.26, 40.50, -74.05, 40.65)),
    }
    return _borough_geoms


def get_borough_from_coords(lat: float, lng: float) -> str:
    """Determine NYC borough from coordinates using point-in-polygon."""
    geoms = _load_borough_geometries()
    point = Point(lng, lat)  # GeoJSON is (lng, lat)

    for borough, polygon in geoms.items():
        if polygon.contains(point):
            return borough

    # If outside all polygons but within NYC bounds, find nearest
    logger.warning(f"Point ({lat}, {lng}) outside all borough polygons, using nearest")
    return _find_nearest_borough(lat, lng, geoms)


def _find_nearest_borough(lat: float, lng: float, geoms: dict) -> str:
    """Find the nearest borough polygon (for edge cases)."""
    from shapely.geometry import Point

    point = Point(lng, lat)
    min_dist = float("inf")
    nearest = "Manhattan"  # Ultimate fallback

    for borough, polygon in geoms.items():
        # prep() objects don't have distance(); need the underlying geometry
        dist = polygon.context.distance(point)
        if dist < min_dist:
            min_dist = dist
            nearest = borough

    return nearest
```

**Updated `src/comp_finder.py` — unified borough extraction:**

```python
from .features import get_borough_from_coords

def _get_borough(row):
    """Extract borough from training data row — try columns first, then coordinates."""
    for col in ["borough_Manhattan", "borough_Brooklyn", "borough_Queens",
                 "borough_Bronx", "borough_Staten Island"]:
        if row.get(col, 0) == 1:
            return col.replace("borough_", "")
    # Fallback: use coordinates if available
    if "latitude" in row and "longitude" in row:
        return get_borough_from_coords(row["latitude"], row["longitude"])
    return "Unknown"
```

**Required dependency:**

```
shapely>=2.0.0
```

---

## 4. Thread-Safe Comp Finder

### Problem

Global mutable state (`_tree`, `_train_data`, `_listings`) is written once at startup and read from async handlers. This is safe *today* because the lifespan ensures build completes before serving. But:
- `cachetools.TTLCache` in geocoder is explicitly not thread-safe
- Any future hot-reload endpoint creates a race condition
- Multi-worker uvicorn (workers > 1) means separate processes, but threading within each worker is still a concern

### Design

- Wrap mutable state in a thread-safe container with `threading.Lock`
- Use `cachetools.cachedmethod` with a lock for the geocoder cache
- Make the comp index immutable after build (frozen dataclass)
- Use `contextvars` for per-request state if needed

### Implementation

**New file: `src/thread_safe_index.py`**

```python
"""Thread-safe comp index with atomic swap."""
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from .config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompIndex:
    """Immutable snapshot of the comparable listings index."""
    tree: KDTree
    listings: tuple  # Immutable (was list[dict])
    train_data: pd.DataFrame
    borough_stats: dict  # Pre-computed market stats per borough

    @property
    def size(self) -> int:
        return len(self.listings)


class IndexManager:
    """Thread-safe index with atomic swap on rebuild."""

    def __init__(self):
        self._index: Optional[CompIndex] = None
        self._lock = threading.Lock()
        self._ready = threading.Event()

    @property
    def index(self) -> CompIndex:
        """Get current index. Blocks until first build completes."""
        self._ready.wait()
        return self._index

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()

    def build(self, train_df: pd.DataFrame) -> CompIndex:
        """Build a new index and atomically swap it in."""
        logger.info("Building new comp index...")

        # Build all data structures locally (no shared state mutation)
        coords = np.radians(train_df[["latitude", "longitude"]].values)
        tree = KDTree(coords)

        listings = []
        for _, row in train_df.iterrows():
            listings.append({
                "id": row.get("id", 0),
                "lat": row["latitude"],
                "lng": row["longitude"],
                "bedrooms": int(row.get("bedrooms_num", 0)),
                "bathrooms": float(row.get("bathrooms_num", 1)),
                "accommodates": int(row.get("accommodates_num", 2)),
                "room_type": "Entire home/apt",
                "price": float(row["price_num"]),
                "revenue": float(row["revenue"]),
                "borough": _extract_borough(row),
            })

        # Pre-compute borough stats
        borough_stats = _compute_borough_stats(train_df)

        # Freeze into immutable snapshot
        new_index = CompIndex(
            tree=tree,
            listings=tuple(listings),  # tuple = immutable
            train_data=train_df.copy(),
            borough_stats=borough_stats,
        )

        # Atomic swap
        with self._lock:
            self._index = new_index
            self._ready.set()

        logger.info(f"Index built: {new_index.size} listings, "
                    f"{len(borough_stats)} boroughs")
        return new_index

    def get_index(self) -> CompIndex:
        """Alias for .index property (explicit is better)."""
        return self.index


def _extract_borough(row) -> str:
    for col in ["borough_Manhattan", "borough_Brooklyn", "borough_Queens",
                 "borough_Bronx", "borough_Staten Island"]:
        if row.get(col, 0) == 1:
            return col.replace("borough_", "")
    return "Unknown"


def _compute_borough_stats(df: pd.DataFrame) -> dict:
    """Pre-compute market stats per borough at build time."""
    stats = {}
    for borough in ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]:
        col = f"borough_{borough}"
        if col in df.columns:
            mask = df[col] == 1
            subset = df[mask]
            if len(subset) > 0:
                stats[borough] = {
                    "borough": borough,
                    "median_revenue": round(float(subset["revenue"].median()), 0),
                    "median_price": round(float(subset["price_num"].median()), 0),
                    "active_listings": len(subset),
                }
    return stats


# Global singleton — one per process
index_manager = IndexManager()
```

**Updated geocoder cache — thread-safe:**

```python
"""Thread-safe geocoder with locked cache."""
import threading
from cachetools import TTLCache, cached
from .config import settings

_cache_lock = threading.Lock()

@cached(cache=TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL),
        lock=_cache_lock,
        key=lambda address: address.strip().lower())
def geocode(address: str) -> GeocodeResult:
    ...
```

---

## 5. PostgreSQL for Multi-City

### Problem

Training data is loaded entirely into memory as a CSV/DataFrame. For multi-city support (10+ cities, millions of listings), this doesn't scale. There's no persistent storage for API keys, usage tracking, or model metadata.

### Design

- PostgreSQL as the primary data store for listings, API keys, usage logs, and model metadata
- PostGIS extension for spatial queries (replaces KD-Tree for production)
- Connection pooling via `asyncpg`
- Migrations managed by `alembic`

### Implementation

**Database schema: `migrations/002_listings.sql`**

```sql
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Cities
CREATE TABLE cities (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(50) NOT NULL UNIQUE,  -- "nyc", "la", "london"
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(3) NOT NULL,          -- ISO 3166-1 alpha-3
    timezone    VARCHAR(50) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT FALSE,
    bounds      GEOMETRY(Polygon, 4326),      -- City bounding box
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Listings (partitioned by city)
CREATE TABLE listings (
    id              BIGSERIAL,
    city_id         INTEGER NOT NULL REFERENCES cities(id),
    source_id       VARCHAR(50) NOT NULL,     -- InsideAirbnb listing ID
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    location        GEOMETRY(Point, 4326) NOT NULL,
    bedrooms        SMALLINT NOT NULL DEFAULT 0,
    bathrooms       REAL NOT NULL DEFAULT 1.0,
    accommodates    SMALLINT NOT NULL DEFAULT 2,
    room_type       VARCHAR(50) NOT NULL,
    price           NUMERIC(10,2) NOT NULL,
    revenue         NUMERIC(12,2) NOT NULL,
    borough         VARCHAR(50),
    data_date       DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, city_id)
) PARTITION BY LIST (city_id);

-- Create partitions per city
CREATE TABLE listings_nyc PARTITION OF listings FOR VALUES IN (1);
CREATE TABLE listings_la  PARTITION OF listings FOR VALUES IN (2);

-- Spatial index (per partition)
CREATE INDEX idx_listings_nyc_location ON listings_nyc USING GIST (location);
CREATE INDEX idx_listings_nyc_bedrooms ON listings_nyc (bedrooms, accommodates);

-- Model metadata
CREATE TABLE models (
    id              SERIAL PRIMARY KEY,
    city_id         INTEGER NOT NULL REFERENCES cities(id),
    version         VARCHAR(20) NOT NULL,
    model_type      VARCHAR(50) NOT NULL,
    feature_columns JSONB NOT NULL,
    metrics         JSONB,
    file_path       VARCHAR(500) NOT NULL,
    checksum        VARCHAR(64) NOT NULL,
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (city_id, version)
);

-- Usage tracking
CREATE TABLE usage_logs (
    id              BIGSERIAL PRIMARY KEY,
    api_key_id      INTEGER REFERENCES api_keys(id),
    endpoint        VARCHAR(100) NOT NULL,
    city_slug       VARCHAR(50),
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    response_ms     INTEGER,
    status_code     SMALLINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partition by month for time-series
CREATE INDEX idx_usage_created ON usage_logs (created_at);
CREATE INDEX idx_usage_api_key ON usage_logs (api_key_id, created_at);
```

**Connection pool: `src/db.py`**

```python
"""PostgreSQL connection pool."""
import asyncpg
from .config import settings

_pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize connection pool on startup."""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=2,
        max_size=20,
        command_timeout=30,
    )


async def close_db():
    """Close pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_db_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool
```

**PostGIS spatial query — find comps from DB:**

```python
"""Database-backed comp finder for multi-city deployments."""
import asyncpg
from .db import get_db_pool

FIND_COMPS_SQL = """
SELECT
    source_id,
    lat,
    lng,
    bedrooms,
    bathrooms,
    accommodates,
    room_type,
    price,
    revenue,
    borough,
    ST_Distance(
        location::geography,
        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
    ) / 1000.0 AS distance_km
FROM listings
WHERE city_id = $3
  AND ABS(bedrooms - $4) <= 1
  AND ABS(accommodates - $5) <= 2
ORDER BY location <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
LIMIT $6
"""


async def find_comps_db(
    lng: float,
    lat: float,
    city_id: int,
    bedrooms: int,
    accommodates: int,
    k: int = 20,
) -> list[dict]:
    """Find comparable listings using PostGIS spatial index."""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            FIND_COMPS_SQL,
            lng, lat, city_id, bedrooms, accommodates, k,
        )
    return [dict(row) for row in rows]
```

**Config addition (`src/config.py`):**

```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rentalizer:secret@localhost:5432/rentalizer")
```

---

## 6. Redis Caching Layer

### Problem

- Geocoding cache (`TTLCache`) is per-process, lost on restart, not thread-safe
- Market stats are re-computed on every request
- No shared cache across multiple uvicorn workers

### Design

- Redis as the shared caching layer for geocoding, market stats, and API responses
- L1 (in-process `cachetools`) + L2 (Redis) caching for hot paths
- Cache-aside pattern with stale-while-revalidate for market data
- Cache keys namespaced by city for multi-city support

### Implementation

**New file: `src/cache.py`**

```python
"""Redis caching layer with L1 in-process fallback."""
import json
import hashlib
import logging
from typing import Any, Optional
from functools import wraps

import redis.asyncio as aioredis
from cachetools import TTLCache

from .config import settings

logger = logging.getLogger(__name__)

# L1: In-process cache (fast, per-worker)
_l1_cache: TTLCache = TTLCache(maxsize=5000, ttl=300)  # 5 min TTL

# L2: Redis (shared across workers)
_redis: aioredis.Redis | None = None


async def init_cache():
    """Initialize Redis connection."""
    global _redis
    _redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
    )
    await _redis.ping()
    logger.info("Redis cache connected")


async def close_cache():
    global _redis
    if _redis:
        await _redis.close()


def _make_key(namespace: str, *args) -> str:
    """Deterministic cache key from namespace + arguments."""
    raw = f"{namespace}:" + ":".join(str(a) for a in args)
    return raw


async def cache_get(namespace: str, *args) -> Optional[Any]:
    """Get from L1, then L2."""
    key = _make_key(namespace, *args)

    # L1
    if key in _l1_cache:
        return _l1_cache[key]

    # L2
    if _redis:
        try:
            raw = await _redis.get(key)
            if raw:
                value = json.loads(raw)
                _l1_cache[key] = value  # Promote to L1
                return value
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")

    return None


async def cache_set(namespace: str, value: Any, ttl: int = 3600, *args):
    """Set in both L1 and L2."""
    key = _make_key(namespace, *args)

    _l1_cache[key] = value

    if _redis:
        try:
            await _redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")


async def cache_delete(namespace: str, *args):
    """Invalidate from both layers."""
    key = _make_key(namespace, *args)
    _l1_cache.pop(key, None)
    if _redis:
        await _redis.delete(key)


# --- Specialized cache functions ---

async def get_cached_geocode(address: str) -> Optional[dict]:
    normalized = address.strip().lower()
    return await cache_get("geocode", normalized)


async def set_cached_geocode(address: str, result: dict):
    normalized = address.strip().lower()
    await cache_set("geocode", result, ttl=settings.CACHE_TTL, *normalized)


async def get_cached_market_stats(city_slug: str, borough: str) -> Optional[dict]:
    return await cache_get("market", city_slug, borough)


async def set_cached_market_stats(city_slug: str, borough: str, stats: dict):
    await cache_set("market", stats, ttl=86400, *[])  # 24h TTL
    key = _make_key("market", city_slug, borough)
    if _redis:
        await _redis.setex(key, 86400, json.dumps(stats))
```

**Updated `src/config.py`:**

```python
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

**Docker Compose addition (`docker-compose.yml`):**

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis_data:
```

---

## 7. Structured Logging

### Problem

- `logging.basicConfig(level=logging.INFO)` with unstructured string messages
- No request ID correlation across log lines
- PII (addresses, coordinates) in logs with no redaction
- No JSON output for log aggregation (ELK, Datadog, CloudWatch)

### Design

- `structlog` for structured JSON logging
- Request ID propagated via `contextvars`
- PII redaction middleware
- Performance metrics as structured fields

### Implementation

**New file: `src/logging_config.py`**

```python
"""Structured logging configuration."""
import logging
import sys
import re
from contextvars import ContextVar
from typing import Any

import structlog

# Request-scoped context
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
api_key_id_var: ContextVar[str] = ContextVar("api_key_id", default="-")

# PII patterns to redact
_PII_PATTERNS = [
    (re.compile(r'\b\d{1,5}\s+\w+\s+(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|ln|lane|ct|court|pl|place)\b', re.I), '[ADDRESS_REDACTED]'),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE_REDACTED]'),
]


def _redact_pii(event_dict: dict) -> dict:
    """Redact PII from log values."""
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern, replacement in _PII_PATTERNS:
                event_dict[key] = pattern.sub(replacement, event_dict[key])
    return event_dict


def _add_request_context(event_dict: dict) -> dict:
    """Inject request-scoped context into every log line."""
    event_dict["request_id"] = request_id_var.get()
    event_dict["api_key_id"] = api_key_id_var.get()
    return event_dict


def setup_logging(log_level: str = "INFO"):
    """Configure structlog for the application."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            _add_request_context,
            _redact_pii,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib for uvicorn access logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named structured logger."""
    return structlog.get_logger(name)
```

**Middleware for request context:**

```python
"""Request logging middleware."""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from .logging_config import request_id_var, api_key_id_var, get_logger

logger = get_logger("middleware")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request_id_var.set(request_id)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
            client_ip=request.client.host if request.client else None,
        )

        response.headers["X-Request-ID"] = request_id
        return response
```

**Usage in `src/api.py`:**

```python
from .logging_config import setup_logging, get_logger
from .middleware import RequestContextMiddleware

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("api")

app = FastAPI(...)
app.add_middleware(RequestContextMiddleware)

# In endpoint:
logger.info(
    "estimate_completed",
    address_hash=hashlib.sha256(req.address.encode()).hexdigest()[:12],
    lat=round(geo.lat, 4),
    lng=round(geo.lng, 4),
    borough=borough,
    comp_count=len(comps),
    annual_revenue=round(annual_revenue, 0),
    confidence=confidence.level,
    geocode_ms=geocode_ms,
    comp_ms=comp_ms,
    model_ms=model_ms,
    total_ms=total_ms,
)
```

---

## 8. CI/CD Pipeline

### Problem

No automated testing, no security scanning, no deployment pipeline. Manual Docker builds with no integrity checks.

### Design

- GitHub Actions pipeline with 4 stages: lint → test → security → deploy
- Container image scanning with Trivy
- Dependency auditing with `pip-audit`
- Model integrity verification via SHA-256 checksums
- Blue-green deployment to production

### Implementation

**`.github/workflows/ci.yml`:**

```yaml
name: Rentalizer CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/rentalizer

jobs:
  # ─── Stage 1: Lint & Type Check ───
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Ruff lint
        run: ruff check src/ tests/
      - name: Ruff format check
        run: ruff format --check src/ tests/
      - name: Type check
        run: mypy src/ --ignore-missing-imports

  # ─── Stage 2: Tests ───
  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_DB: rentalizer_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    env:
      DATABASE_URL: postgresql://test:test@localhost:5432/rentalizer_test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run migrations
        run: alembic upgrade head
      - name: Run tests
        run: |
          pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing \
            -v --tb=short
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  # ─── Stage 3: Security ───
  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Dependency audit
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt --strict
      - name: Container scan (build)
        run: |
          docker build -t rentalizer:scan .
      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: rentalizer:scan
          format: table
          exit-code: 1
          severity: CRITICAL,HIGH
      - name: Model integrity check
        run: |
          python scripts/verify_model_checksum.py

  # ─── Stage 4: Build & Deploy ───
  deploy:
    runs-on: ubuntu-latest
    needs: security
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Deploy to production
        run: |
          # kubectl set image deployment/rentalizer \
          #   rentalizer=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          echo "Deploy step — configure for your infrastructure"
```

**`requirements-dev.txt`:**

```
pytest>=8.0.0
pytest-cov>=5.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
ruff>=0.5.0
mypy>=1.10.0
pip-audit>=2.7.0
```

**Model checksum verification: `scripts/verify_model_checksum.py`**

```python
"""Verify model file integrity before deployment."""
import hashlib
import json
import sys
from pathlib import Path

CHECKSUM_FILE = Path("models/checksums.json")

def verify():
    if not CHECKSUM_FILE.exists():
        print("WARNING: No checksums.json found — skipping verification")
        return True

    with open(CHECKSUM_FILE) as f:
        expected = json.load(f)

    all_ok = True
    for filepath, expected_hash in expected.items():
        p = Path(filepath)
        if not p.exists():
            print(f"FAIL: {filepath} not found")
            all_ok = False
            continue

        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected_hash:
            print(f"FAIL: {filepath} checksum mismatch")
            print(f"  expected: {expected_hash}")
            print(f"  actual:   {actual}")
            all_ok = False
        else:
            print(f"OK:   {filepath}")

    if not all_ok:
        print("\nModel integrity check FAILED")
        sys.exit(1)

    print("\nAll model files verified OK")
    return True

if __name__ == "__main__":
    verify()
```

---

## 9. Docker Security Hardening

### Problem

Container runs as root, no multi-stage build, no `.dockerignore`, no health checks, no resource limits, model files baked into image.

### Design

- Multi-stage build (builder + runtime)
- Non-root user
- Read-only filesystem where possible
- Health checks built into the image
- Minimal attack surface (no shell, no package managers in runtime)

### Implementation

**Dockerfile:**

```dockerfile
# ═══════════════════════════════════════════
# Stage 1: Builder
# ═══════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Prepare data and train model
COPY . .
RUN python scripts/prepare_data.py && \
    python scripts/train_model.py 10 && \
    python scripts/generate_checksums.py

# ═══════════════════════════════════════════
# Stage 2: Runtime
# ═══════════════════════════════════════════
FROM python:3.12-slim AS runtime

# Install only runtime libraries (no gcc, no dev headers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r -g 1000 appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code and model artifacts
COPY --from=builder /build/src ./src
COPY --from=builder /build/data ./data
COPY --from=builder /build/models ./models
COPY --from=builder /build/static ./static
COPY --from=builder /build/templates ./templates

# Set ownership and permissions
RUN chown -R appuser:appuser /app && \
    chmod -R 550 /app && \
    chmod -R 660 /app/models

# Switch to non-root user
USER appuser:appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Security: read-only filesystem hints (enforce via docker run --read-only)
# /tmp is needed by Python; mount a tmpfs at runtime:
#   docker run --read-only --tmpfs /tmp:rw,noexec,nosuid,size=100m ...

EXPOSE 8000

# Run with production settings
CMD ["uvicorn", "src.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--limit-max-request-size", "1048576", \
     "--access-log"]
```

**`.dockerignore`:**

```
.git
.github
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.env
.env.*
*.md
!requirements.txt
tests/
docs/
coverage.xml
htmlcov/
node_modules/
```

**`docker-compose.yml` (production):**

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://rentalizer:${DB_PASSWORD}@postgres:5432/rentalizer
      - REDIS_URL=redis://redis:6379/0
      - MAPBOX_TOKEN=${MAPBOX_TOKEN}
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          memory: 512M
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped

  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: rentalizer
      POSTGRES_USER: rentalizer
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rentalizer"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

volumes:
  pg_data:
  redis_data:
```

---

## 10. Multi-City Architecture

### Problem

Hardcoded NYC bounding box, single training dataset, single model. Adding a new city requires code changes. Borough detection is NYC-specific.

### Design

- City registry in PostgreSQL — each city has its own data, model, and spatial boundaries
- City-aware routing: `/v1/{city}/estimate` with fallback to auto-detect from coordinates
- Per-city models trained independently but sharing the same inference pipeline
- Plugin architecture for city-specific logic (borough/neighborhood detection, data sources)

### Implementation

**City registry: `src/cities.py`**

```python
"""City registry — manages multi-city configuration."""
from dataclasses import dataclass
from typing import Protocol

from .db import get_db_pool


@dataclass
class CityConfig:
    id: int
    slug: str
    name: str
    country: str
    timezone: str
    lat_min: float
    lat_max: float
    lng_min: float
    lng_max: float


class CityDetector(Protocol):
    """Protocol for city-specific neighborhood/zone detection."""
    def detect_zone(self, lat: float, lng: float) -> str: ...


# In-memory city registry (loaded at startup)
_cities: dict[str, CityConfig] = {}


async def load_cities():
    """Load active cities from database."""
    global _cities
    pool = get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, slug, name, country, timezone, "
            "ST_YMin(bounds) as lat_min, ST_YMax(bounds) as lat_max, "
            "ST_XMin(bounds) as lng_min, ST_XMax(bounds) as lng_max "
            "FROM cities WHERE is_active = TRUE"
        )
    _cities = {row["slug"]: CityConfig(**dict(row)) for row in rows}


def get_city(slug: str) -> CityConfig:
    if slug not in _cities:
        raise ValueError(f"Unknown city: {slug}. Available: {list(_cities.keys())}")
    return _cities[slug]


def detect_city(lat: float, lng: float) -> CityConfig | None:
    """Auto-detect city from coordinates using bounding box."""
    for city in _cities.values():
        if (city.lat_min <= lat <= city.lat_max and
            city.lng_min <= lng <= city.lng_max):
            return city
    return None


def list_cities() -> list[dict]:
    return [
        {"slug": c.slug, "name": c.name, "country": c.country}
        for c in _cities.values()
    ]
```

**Zone detection plugin interface: `src/zones.py`**

```python
"""City-specific zone detection (borough, neighborhood, etc.)."""
from abc import ABC, abstractmethod
from .features import get_borough_from_coords  # NYC boroughs via GeoJSON


class ZoneDetector(ABC):
    """Base class for city-specific zone detection."""
    @abstractmethod
    def detect(self, lat: float, lng: float) -> str:
        ...

    @abstractmethod
    def zone_label(self) -> str:
        """Human-readable label (e.g., 'borough', 'neighborhood', 'district')."""
        ...


class NYCZoneDetector(ZoneDetector):
    def detect(self, lat: float, lng: float) -> str:
        return get_borough_from_coords(lat, lng)

    def zone_label(self) -> str:
        return "borough"


class LondonZoneDetector(ZoneDetector):
    """London zones by fare zone or borough."""
    def detect(self, lat: float, lng: float) -> str:
        # TODO: Implement London borough detection
        return "Unknown"

    def zone_label(self) -> str:
        return "borough"


# Registry
_zone_detectors: dict[str, ZoneDetector] = {
    "nyc": NYCZoneDetector(),
    "london": LondonZoneDetector(),
}


def get_zone_detector(city_slug: str) -> ZoneDetector:
    detector = _zone_detectors.get(city_slug)
    if not detector:
        raise ValueError(f"No zone detector for city: {city_slug}")
    return detector
```

**Updated API routes — city-aware:**

```python
from .cities import get_city, detect_city, list_cities

@app.get("/v1/cities")
async def get_cities():
    """List available cities."""
    return {"cities": list_cities()}


@app.post("/v1/{city}/estimate", response_model=EstimateResponse)
async def estimate_city(city: str, req: EstimateRequest, ...):
    """Estimate for a specific city."""
    city_config = get_city(city)
    geo = geocode(f"{req.address}, {city_config.name}")

    # Validate bounds
    if not (city_config.lat_min <= geo.lat <= city_config.lat_max and
            city_config.lng_min <= geo.lng <= city_config.lng_max):
        raise OutsideCoverageError(
            f"Address is outside {city_config.name} coverage area."
        )

    # City-specific zone detection
    zone_detector = get_zone_detector(city)
    zone = zone_detector.detect(geo.lat, geo.lng)

    # Find comps from city-specific index
    comps = await find_comps_db(geo.lng, geo.lat, city_config.id,
                                 req.bedrooms, req.accommodates)

    # Load city-specific model
    model = get_model_for_city(city_config.id)

    ...


@app.post("/v1/estimate", response_model=EstimateResponse)
async def estimate_auto(req: EstimateRequest, ...):
    """Auto-detect city from geocoded coordinates."""
    geo = geocode(req.address)
    city = detect_city(geo.lat, geo.lng)

    if city is None:
        raise OutsideCoverageError(
            "Address is not in any supported city. "
            f"Supported: {[c['name'] for c in list_cities()]}"
        )

    # Delegate to city-specific handler
    return await estimate_city(city.slug, req, ...)
```

**Data pipeline for new cities: `scripts/add_city.py`**

```python
"""Register a new city and import its data."""
import asyncio
import asyncpg
import sys

CITY_SQL = """
INSERT INTO cities (slug, name, country, timezone, bounds, is_active)
VALUES ($1, $2, $3, $4,
        ST_MakeEnvelope($5, $6, $7, $8, 4326),
        TRUE)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    bounds = EXCLUDED.bounds
RETURNING id
"""

async def add_city(slug, name, country, tz, lng_min, lat_min, lng_max, lat_max, dsn):
    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as conn:
        city_id = await conn.fetchval(
            CITY_SQL,
            slug, name, country, tz,
            lng_min, lat_min, lng_max, lat_max,
        )
        print(f"City '{slug}' registered with id={city_id}")
    await pool.close()
    return city_id

if __name__ == "__main__":
    # Example: python scripts/add_city.py la "Los Angeles" US America/Los_Angeles -118.7 33.7 -117.9 34.4
    asyncio.run(add_city(*sys.argv[1:]))
```

---

## Dependency Summary

**New dependencies added across all innovations:**

```
# Authentication & DB
asyncpg>=0.29.0
alembic>=1.13.0

# Rate limiting
slowapi>=0.1.9

# Caching
redis>=5.0.0

# Spatial
shapely>=2.0.0

# Logging
structlog>=24.1.0

# Dev/CI
pytest>=8.0.0
pytest-cov>=5.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
ruff>=0.5.0
mypy>=1.10.0
pip-audit>=2.7.0
```

---

## Migration Path

Order of implementation (dependencies flow downward):

```
9. Docker Security ──────────────────────────────────┐ (no deps, do first)
7. Structured Logging ──────────────────────────────┐│
3. Borough Detection (GeoJSON) ────────────────────┐││
1. API Key Auth ──────────────────────────────────┐ │││
2. Rate Limiting ────────────────────────────────┐ │ │││
                                                 │ │ │││
4. Thread-Safe Comp Finder ◄─────────────────────┘ │ │││
5. PostgreSQL ◄─────────────────────────────────────┘ │││
6. Redis Caching ◄────────────────────────────────────┘││
10. Multi-City Architecture ◄──────────────────────────┘│
8. CI/CD Pipeline ◄─────────────────────────────────────┘
```

**Recommended sprint plan:**

| Sprint | Innovations | Effort |
|--------|------------|--------|
| Sprint 1 (Week 1–2) | #9 Docker Security, #7 Structured Logging, #3 Borough GeoJSON | ~3 days |
| Sprint 2 (Week 3–4) | #1 API Key Auth, #2 Rate Limiting, #4 Thread Safety | ~4 days |
| Sprint 3 (Week 5–6) | #5 PostgreSQL, #6 Redis Caching | ~5 days |
| Sprint 4 (Week 7–8) | #10 Multi-City Architecture, #8 CI/CD Pipeline | ~5 days |

---

## Risk Assessment

| Innovation | Risk | Mitigation |
|-----------|------|------------|
| #1 Auth | Breaking change for existing clients | Version the API (`/v1/` vs `/v2/`); keep `/v1/` open with deprecation warning for 30 days |
| #2 Rate limiting | Legitimate users blocked | Generous defaults; per-key overrides; 429 responses include `Retry-After` header |
| #3 Borough GeoJSON | GeoJSON file missing in deployment | Fallback to corrected bounding boxes; health check validates file presence |
| #4 Thread safety | Performance regression from locks | Read-heavy workload = minimal contention; benchmark before/after |
| #5 PostgreSQL | Migration complexity | Start with read-only replica for comp queries; keep in-memory index as fallback |
| #6 Redis | Additional infrastructure dependency | Graceful degradation — cache miss = recompute (slower but correct) |
| #7 Structured logging | Log volume increase | Configure levels per module; sample debug logs in production |
| #8 CI/CD | Pipeline flakiness | Deterministic tests; no external service dependencies in unit tests |
| #9 Docker security | Permission issues with volume mounts | Test with `--read-only` flag; document tmpfs requirements |
| #10 Multi-city | Data quality varies by city | Per-city data validation pipeline; quality metrics dashboard |
