# Engineering Audit: Rentalizer Clone — Revenue Prediction API

**Auditor:** Senior Backend Engineer  
**Date:** 2026-06-29  
**Verdict:** ⚠️ Solid MVP prototype with several critical production gaps

---

## 1. Framework Choice — Is FastAPI the Right Call?

**Verdict: ✅ FastAPI is fine for MVP. Not the only option.**

**Strengths:**
- Async support, auto-generated OpenAPI docs, Pydantic validation — all good for a prediction API
- Fast iteration speed for a 3-day build
- Native type hints align well with ML serving

**Concerns:**
- For production ML serving at scale, consider **TorchServe**, **TensorFlow Serving**, or **BentoML** — they handle model lifecycle (versioning, A/B testing, canary deploys) out of the box
- If latency is critical (<50ms p99), a compiled framework (**Rust/Actix**, **Go/Gin**) with the model exported to ONNX would outperform Python significantly
- For MVP: FastAPI is the right choice. For production: you'll likely graduate to a dedicated model server

**Recommendation:** Stick with FastAPI for now, but design the model loading layer so it can be swapped later.

---

## 2. Geocoding — Nominatim Reliability

**Verdict: ❌ Nominatim is not reliable enough for a production API.**

**Critical issues:**
- **Rate limits:** Nominatim's public instance limits to **1 request/second** (OSM usage policy). This kills batch endpoints and concurrent users.
- **Uptime:** Public Nominatim is community-run. No SLA. Frequent slowdowns and outages.
- **Accuracy:** Nominatim returns OpenStreetMap results. Address parsing is inconsistent — "350 5th Ave" vs "350 Fifth Avenue" may return different coordinates or fail entirely.
- **No apartment/unit support:** Nominatim can't geocode "Unit 4B, 350 5th Ave"

**Alternatives (ranked):**
1. **Mapbox Geocoding API** — Best accuracy, generous free tier (100K/mo), structured address support
2. **Google Maps Geocoding** — Gold standard accuracy, but $5/1K requests (expensive at scale)
3. **Pelican (self-hosted Nominatim)** — Free, unlimited, but requires OSM data hosting (~50GB for US) and maintenance
4. **HERE Geocoding** — Good free tier, decent accuracy

**Recommendation:** Use **Mapbox** as primary (good free tier, reliable), Nominatim as fallback. Cache aggressively (see §6).

---

## 3. Comp Finding — In-Memory Scalability

**Verdict: ❌ Does not scale. Works for 5K listings. Breaks at 100K+.**

**Current approach:** "Load all labeled listings into memory, find K nearest"

**Memory math:**
- 5,000 listings × ~20 features × 8 bytes ≈ **0.8 MB** — fits in memory trivially
- 100K listings ≈ **16 MB** — still fits, but brute-force nearest-neighbor is O(n) per query
- 1M listings ≈ **160 MB** — manageable, but O(n) scan per request at ~1ms means **1 second per query**

**The real problem is algorithmic, not memory:**
- Brute-force KNN over 100K+ points = ~100ms per query (Python), which is unacceptable for a real-time API
- Need spatial indexing: **KD-Tree** (scipy), **Ball Tree**, or **PostGIS spatial index**

**Recommendation:**
- **MVP (5K listings):** Load into memory, use `scipy.spatial.KDTree` — sub-millisecond queries
- **Production (100K+):** Use **PostGIS** with GiST spatial index, or load into a **FAISS** index for approximate nearest-neighbor
- **Hybrid:** Keep the comp-finder in memory for the current dataset, but abstract the interface so it can be swapped to PostGIS later

**Also missing:** The plan says "load all labeled listings into memory" but never specifies when this happens. On startup? Per-request? This needs to be explicit:
```python
# On startup
@app.on_event("startup")
def load_listings():
    app.state.listings = load_and_index("data/train.csv")
```

---

## 4. API Design — RESTfulness & Completeness

**Verdict: ⚠️ Functional but incomplete. Several missing endpoints and design issues.**

**What's good:**
- POST for estimation (correct — this is not idempotent lookup)
- Batch endpoint planned
- Response includes comps and confidence (good for transparency)

**What's missing:**

| Missing Endpoint | Purpose |
|---|---|
| `GET /v1/health` | Health check for load balancers/orchestrators |
| `GET /v1/ready` | Readiness probe (model loaded?) |
| `GET /v1/market/{borough}` | Market stats without estimation |
| `GET /v1/comps?lat=X&lng=Y` | Direct comp lookup (useful for debugging) |
| `GET /v1/model/info` | Model version, training date, feature list |
| `GET /v1/metrics` | Prometheus metrics for monitoring |

**Design issues:**
1. **No versioning strategy.** `/v1/` is there, but what happens when the model changes? Response schema must be backward-compatible.
2. **No request ID.** Every response should include a `request_id` for debugging and log correlation.
3. **No rate limiting.** Public API needs rate limiting from day one. Use `slowapi` or a reverse proxy.
4. **Batch endpoint has no size limit.** What happens if someone sends 10,000 addresses? Need a max batch size (e.g., 100).
5. **No pagination on comps.** If there are 20 comps, return them all. But the spec should cap it (top 10-20).
6. **monthly_revenue array is unexplained.** Where does this come from? The model predicts annual revenue. Are these seasonal adjustments? This needs to be specified.

**Recommendation:** Add health/readiness probes, request IDs, rate limiting, and batch size limits.

---

## 5. Error Handling — Failure Modes

**Verdict: ❌ Not addressed. This is a critical gap.**

The plan describes happy paths only. Here's what needs explicit handling:

| Failure | Impact | Required Response |
|---|---|---|
| Geocoding fails (address not found) | No comps can be found | 422 with `{"error": "geocoding_failed", "suggestion": "Try a more specific address"}` |
| Geocoding returns wrong location | Bad comps, bad prediction | Validate geocoded result is in NYC bounds (lat 40.4-41.0, lng -74.3 to -73.7) |
| No comps found (remote area) | No comp-based estimate | Fall back to XGBoost-only with `confidence: "low"` |
| Few comps found (<5) | Weak statistical basis | Return prediction with `confidence: "low"` and warn in response |
| Model prediction returns negative | Nonsensical output | Clamp to 0, log warning |
| Model not loaded yet (cold start) | 500 error | Return 503 with retry-after header |
| Invalid input (bedrooms=-1) | Garbage in, garbage out | Pydantic validation with clear error messages |
| Nominatim rate limited | Geocoding blocked | Circuit breaker pattern, fall back to Mapbox, or return 429 |
| Batch request too large | Memory/time exhaustion | 413 with max size in error message |

**Recommendation:** Implement a proper error hierarchy with custom exception classes and FastAPI exception handlers.

```python
class GeocodingError(Exception): ...
class InsufficientCompsError(Exception): ...
class ModelNotReadyError(Exception): ...
```

---

## 6. Caching Strategy

**Verdict: ❌ "Cache geocoding results" is insufficient. Need a concrete strategy.**

**What to cache:**

| Item | TTL | Key | Why |
|---|---|---|---|
| Geocoding results | **7 days** | Normalized address string | Addresses don't move. Cache aggressively. |
| Comp results | **1 hour** | Rounded lat/lng (3 decimal places ≈ 111m) | Nearby addresses share comps. Rounding prevents cache fragmentation. |
| Market stats (borough) | **24 hours** | Borough name | Changes quarterly, but cache daily for safety. |
| Model predictions | **4 hours** | Hash of (lat, lng, beds, baths, accommodates, price) | Same inputs → same output. Prevents re-computation. |

**Cache implementation:**
- **MVP:** In-memory dict with TTL (e.g., `cachetools.TTLCache`)
- **Production:** Redis with appropriate TTLs and eviction policies

**Cache invalidation:** The plan says nothing about this. When new InsideAirbnb data arrives (quarterly), all caches must be flushed. Need a `POST /v1/admin/cache/clear` endpoint or a versioned cache key.

**Recommendation:** Use `cachetools.TTLCache` for MVP. Add cache key versioning tied to model/data version.

---

## 7. Database — PostgreSQL/PostGIS vs In-Memory

**Verdict: MVP: in-memory is fine. Production: PostgreSQL/PostGIS is necessary.**

**In-memory pros:**
- Zero infrastructure. Single Python process.
- Sub-millisecond comp queries with KD-Tree
- Simple deployment

**In-memory cons:**
- Cold start: loading 5K listings on every restart (~100ms, acceptable)
- No persistence: if the process dies, state is lost (but data is on disk, so just reload)
- Can't share state across multiple API instances (horizontal scaling blocked)
- Can't do complex queries (e.g., "average revenue by borough for 2BR apartments")

**PostgreSQL/PostGIS pros:**
- Spatial indexing (`GiST`) for efficient nearest-neighbor queries
- Concurrent access from multiple API instances
- SQL for analytics queries
- Data persistence and ACID guarantees
- Can store model metadata, prediction logs, audit trail

**Recommendation:**
- **MVP:** In-memory with KD-Tree. Good enough for 5K listings, single instance.
- **Production (if scaling beyond one city):** PostgreSQL/PostGIS. Use `geoalchemy2` for spatial queries. Add `pg_trgm` for fuzzy address matching.

---

## 8. File Structure — Missing Modules

**Verdict: ⚠️ Functional but missing several critical modules.**

**Current structure:**
```
src/
├── prepare_data.py
├── train_model.py
├── comp_finder.py
├── geocoder.py
└── api.py
```

**What's missing:**

| Module | Purpose |
|---|---|
| `config.py` | Centralized settings (API keys, model paths, cache TTLs, feature lists) |
| `schemas.py` | Pydantic models for request/response validation (FastAPI best practice) |
| `exceptions.py` | Custom exception classes and FastAPI exception handlers |
| `dependencies.py` | FastAPI dependency injection (model loading, DB sessions) |
| `middleware.py` | Request logging, CORS, rate limiting |
| `model_loader.py` | Model loading, versioning, and prediction interface |
| `features.py` | Feature engineering pipeline (shared between training and inference) |
| `cache.py` | Caching layer abstraction |
| `metrics.py` | Prometheus metrics or custom counters |
| `utils.py` | Geocoding normalization, NYC bounds checking, etc. |

**Also missing:**
- `Dockerfile` and `docker-compose.yml` — deployment is an afterthought
- `.env.example` — configuration documentation
- `Makefile` or `pyproject.toml` — build/run commands
- `README.md` — project documentation

**Recommendation:** Add the missing modules. Especially `config.py`, `schemas.py`, and `exceptions.py` — these are non-negotiable for a production FastAPI app.

---

## 9. Deployment

**Verdict: ❌ Not addressed at all. This is a significant gap.**

**What's needed:**

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Infrastructure (minimum viable production):**
- Single container on **Railway**, **Fly.io**, or **AWS ECS Fargate**
- Redis for caching (managed, e.g., Upstash free tier)
- GitHub Actions for CI/CD (lint, test, deploy on push to main)
- Environment variables for secrets (API keys, model paths)

**Scaling considerations:**
- Model files (~50MB for XGBoost) must be baked into the Docker image or loaded from object storage (S3/GCS)
- Cold start time: model loading + listing indexing = ~2-5 seconds. Use a readiness probe.
- At 100 req/s, a single Python process may struggle. Need multiple workers (`--workers 4`) or horizontal scaling.

**Recommendation:** Add Dockerfile, docker-compose (for local dev with Redis), and a basic CI/CD pipeline.

---

## 10. Performance — Expected Latency

**Verdict: ⚠️ Acceptable for MVP, but no analysis provided.**

**Latency breakdown (estimated):**

| Step | Latency | Notes |
|---|---|---|
| Request parsing | <1ms | Pydantic validation |
| Geocoding | **100-500ms** | Nominatim is slow. Mapbox is ~50ms. This dominates. |
| Cache lookup | <1ms | In-memory dict |
| Comp finding | 1-5ms | KD-Tree on 5K points |
| Feature engineering | <1ms | Simple arithmetic |
| Model prediction | 1-3ms | XGBoost inference |
| Response serialization | <1ms | JSON encoding |
| **Total (cold)** | **100-500ms** | Dominated by geocoding |
| **Total (cached)** | **5-10ms** | If geocoding result is cached |

**Bottleneck:** Geocoding. This is why caching is critical. With a warm cache, the API is fast enough. Without it, 500ms+ per request is unacceptable for batch endpoints.

**Batch endpoint at 100 items:** 100 × 500ms = 50 seconds sequentially. Need parallel geocoding (async with rate limiting) or pre-geocoding.

**Recommendation:**
1. Cache geocoding aggressively (§6)
2. Use `asyncio.gather` for parallel geocoding in batch endpoint, with semaphore for rate limiting
3. Set a hard timeout of 10 seconds per request (503 if exceeded)
4. Profile with `py-spy` or `cProfile` before optimizing

---

## Summary of Critical Issues

| # | Issue | Severity | Action |
|---|---|---|---|
| 1 | Nominatim is unreliable for production | 🔴 High | Switch to Mapbox primary, Nominatim fallback |
| 2 | No error handling defined | 🔴 High | Define failure modes and error responses |
| 3 | In-memory comp finding won't scale | 🟡 Medium | Abstract interface, plan PostGIS migration path |
| 4 | No caching strategy | 🟡 Medium | Define TTLs, implement TTLCache for MVP |
| 5 | Missing API endpoints (health, ready) | 🟡 Medium | Add health/readiness probes |
| 6 | No deployment plan | 🟡 Medium | Add Dockerfile and CI/CD |
| 7 | Missing config/schemas modules | 🟡 Medium | Add FastAPI best-practice modules |
| 8 | Batch endpoint has no size limit | 🟡 Medium | Cap at 100, add parallel geocoding |
| 9 | monthly_revenue source unexplained | 🟠 Low | Document or remove |
| 10 | No request ID or logging | 🟠 Low | Add request middleware |

---

## Bottom Line

This is a **well-thought-out MVP plan** for a 3-day build. The data analysis is sound, the model approach (XGBoost + comp-based ensemble) is sensible, and the architecture is clean. For a prototype or demo, this will work.

But it's **not production-ready**. The gaps in error handling, geocoding reliability, caching, and deployment would cause real problems with real users. The good news: none of these are architectural flaws — they're implementation details that can be added incrementally.

**Grade: B- for production readiness, A- for MVP speed.**

Ship it as a prototype, then iterate on the critical issues above before exposing it to users.
