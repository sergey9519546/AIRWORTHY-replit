# Security Audit — Rentalizer API

**Auditor:** Security Subagent  
**Date:** 2026-06-29  
**Scope:** Full application — API, frontend, dependencies, configuration, containerization  
**Files reviewed:** All files in `src/`, `templates/index.html`, `static/app.js`, `requirements.txt`, `Dockerfile`

---

## Executive Summary

Rentalizer is a well-structured FastAPI application for short-term rental revenue estimation. The codebase demonstrates good practices in several areas (Pydantic validation, structured error handling, env-var-based secrets). However, the application **lacks authentication, rate limiting, CORS configuration, and runs as root in the container** — all of which must be addressed before production deployment.

**Critical findings: 2 | High: 3 | Medium: 5 | Low: 4**

---

## Findings by Severity

### 🔴 CRITICAL

#### C-1: No Authentication or Authorization

**Location:** `src/api.py` — all routes  
**Impact:** Any unauthenticated user can call `/v1/estimate`, `/v1/batch`, `/v1/model/info`, etc. The batch endpoint is particularly dangerous as it allows amplification — a single request can trigger up to 20 expensive estimate calls.

**Evidence:**
```python
@app.post("/v1/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest):
    # No auth check — open to the world
```

**Recommendation:**
- Implement API key authentication via a dependency:
  ```python
  from fastapi import Depends, HTTPException, Security
  from fastapi.security import APIKeyHeader
  
  api_key_header = APIKeyHeader(name="X-API-Key")
  
  async def verify_api_key(api_key: str = Security(api_key_header)):
      if api_key not in VALID_API_KEYS:
          raise HTTPException(status_code=401, detail="Invalid API key")
  ```
- Apply `Depends(verify_api_key)` to all data-returning routes
- Keep `/v1/health` and `/` (UI) public

---

#### C-2: No Rate Limiting

**Location:** `src/api.py` — all routes  
**Impact:** Without rate limiting, an attacker can:
- Exhaust server resources (CPU, memory) via rapid `/v1/estimate` calls
- Amplify via `/v1/batch` (20x per request)
- Geocode at scale, burning Mapbox API quota
- Scrape the entire training dataset through comp responses

**Evidence:**
- No rate limiting middleware, no per-IP tracking, no token bucket
- The batch endpoint multiplies the attack surface by 20x with no additional protection

**Recommendation:**
- Add `slowapi` or a Redis-backed rate limiter:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  
  @app.post("/v1/estimate")
  @limiter.limit("30/minute")
  async def estimate(request: Request, req: EstimateRequest):
      ...
  ```
- Set stricter limits on `/v1/batch` (e.g., 5/minute)
- Add per-API-key quotas if authentication is implemented

---

### 🟠 HIGH

#### H-1: Cross-Site Scripting (XSS) via innerHTML

**Location:** `static/app.js` — `renderResults()` function  
**Impact:** API response fields are injected directly into the DOM via `innerHTML` without sanitization. While the API currently returns trusted data, if an attacker can influence API responses (e.g., via a poisoned geocoding result, or a compromised comp listing), they can execute arbitrary JavaScript in the user's browser.

**Evidence:**
```javascript
document.getElementById('confidence-details').innerHTML = `
    <div class="stat-row"><span class="stat-label">Borough</span>
    <span class="stat-value">${data.market.borough}</span></div>
    // ^^^ borough from API response, injected raw into DOM
`;

// Also:
compsHtml += `<div class="comp-item">
    <span>${comp.borough}</span>  // ^^^ unsanitized
```

**Recommendation:**
- Use `textContent` instead of `innerHTML` for data values, or
- Sanitize with DOMPurify before inserting:
  ```javascript
  import DOMPurify from 'dompurify';
  element.innerHTML = DOMPurify.sanitize(template);
  ```
- Alternatively, use a framework that auto-escapes (React, Vue, or even template literals with text nodes)

---

#### H-2: Container Runs as Root

**Location:** `Dockerfile`  
**Impact:** If an attacker achieves code execution inside the container (e.g., via a deserialization vulnerability in the model loading), they have root privileges, making container escape easier.

**Evidence:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .    # No USER directive — runs as root
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Recommendation:**
```dockerfile
FROM python:3.12-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### H-3: Unsafe Model Deserialization via joblib

**Location:** `src/model.py` — `load_model()`  
**Impact:** `joblib.load()` deserializes Python objects using pickle under the hood. If an attacker can replace the model file (`models/revenue_model.pkl`), they achieve arbitrary code execution. This is a supply-chain / file-integrity risk.

**Evidence:**
```python
_model = joblib.load(settings.MODEL_PATH)  # Arbitrary code execution if file is tampered
```

**Recommendation:**
- Verify model file integrity with a checksum before loading:
  ```python
  import hashlib
  
  def verify_checksum(filepath, expected_sha256):
      with open(filepath, "rb") as f:
          assert hashlib.sha256(f.read()).hexdigest() == expected_sha256
  ```
- Use `safetensors` or ONNX format for model serialization (no arbitrary code execution)
- Restrict write access to the models directory in production

---

### 🟡 MEDIUM

#### M-1: No CORS Configuration

**Location:** `src/api.py`  
**Impact:** Without explicit CORS middleware, the browser's default same-origin policy blocks cross-origin requests. This is actually *secure by default* for a server-rendered app, but:
- If a legitimate frontend on a different domain needs to call the API, it will fail silently
- If CORS is later added as `allow_origins=["*"]` without understanding, it becomes a vulnerability

**Evidence:**
```python
app = FastAPI(...)  # No CORSMiddleware added
```

**Recommendation:**
- If cross-origin access is needed, configure explicitly:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],
      allow_methods=["POST", "GET"],
      allow_headers=["*"],
  )
  ```
- If no cross-origin access is needed, document this as intentional

---

#### M-2: Batch Endpoint Error Leaks Exception Class Names

**Location:** `src/api.py` — `batch_estimate()`  
**Impact:** When a single estimate in a batch fails, the error response includes the Python exception class name, which leaks internal implementation details.

**Evidence:**
```python
except Exception as e:
    results.append({"error": type(e).__name__, "detail": str(e)})
    # ^^^ e.g., "GeocodingError", "ModelNotReadyError", "RuntimeError"
```

**Recommendation:**
```python
except Exception as e:
    logger.exception(f"Batch item failed: {e}")
    results.append({"error": "estimation_failed", "detail": "Could not estimate this property"})
```

---

#### M-3: Mapbox Token Passed as URL Path Component

**Location:** `src/geocoder.py` — `_geocode_mapbox()`  
**Impact:** The Mapbox access token is embedded in the URL path, which means it will appear in:
- Server access logs
- Any intermediate proxy logs
- Network monitoring tools

**Evidence:**
```python
url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
params = {"access_token": settings.MAPBOX_TOKEN, ...}
```

**Recommendation:**
- Pass the token in the `Authorization` header instead (Mapbox supports this)
- Or accept this risk and ensure logs are properly secured

---

#### M-4: No Request Size Limit

**Location:** `src/api.py` — `batch_estimate()` accepts `list[EstimateRequest]`  
**Impact:** A client could send a JSON array with thousands of elements. While Pydantic validates each item, the initial parsing of a massive request body consumes memory.

**Evidence:**
```python
@app.post("/v1/batch")
async def batch_estimate(requests: list[EstimateRequest]):
    # No limit on request body size before parsing
    if len(requests) > settings.MAX_BATCH:
        ...
```

**Recommendation:**
- Add uvicorn's `--limit-max-request-size` flag, or
- Add a middleware to reject oversized requests early:
  ```python
  @app.middleware("http")
  async def limit_body_size(request: Request, call_next):
      if request.headers.get("content-length", 0) > 1_000_000:  # 1MB
          return JSONResponse(status_code=413, content={"error": "request_too_large"})
      return await call_next(request)
  ```

---

#### M-5: Geocoding Cache Poisoning Potential

**Location:** `src/geocoder.py` — `TTLCache`  
**Impact:** The geocoding cache uses the address string as the key. An attacker could send many slightly different addresses to fill the cache (up to 10,000 entries with 7-day TTL), evicting legitimate entries. This is a targeted denial-of-service on cache effectiveness.

**Evidence:**
```python
cache = TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)  # 10k entries, 7 days
```

**Recommendation:**
- Consider per-IP cache partitioning or rate limiting (addresses C-2)
- Reduce `CACHE_MAXSIZE` if 10k is excessive for the expected usage
- This is low priority if rate limiting is implemented

---

### 🟢 LOW

#### L-1: Model Info Endpoint Exposes Internal Metrics

**Location:** `src/api.py` — `/v1/model/info`  
**Impact:** Returns model type, version, feature count, and training metrics. While not directly exploitable, this gives attackers insight into the ML pipeline internals.

**Evidence:**
```python
@app.get("/v1/model/info", response_model=ModelInfoResponse)
async def model_info():
    info = get_model_info()  # Returns model_type, version, n_features, metrics
```

**Recommendation:**
- Restrict to authenticated users, or remove in production
- Alternatively, return only `version` and omit `metrics`

---

#### L-2: Server-Side Request Forgery (SSRF) via Nominatim Fallback

**Location:** `src/geocoder.py` — `_geocode_nominatim()`  
**Impact:** The `geopy` Nominatim geocoder makes outbound HTTP requests to `nominatim.openstreetmap.org`. While the address is user-controlled, the target host is fixed by geopy, so SSRF risk is minimal. However, user input is passed directly into the URL without sanitization.

**Evidence:**
```python
location = geolocator.geocode(address, country_codes="us", limit=1)
# address comes directly from user input
```

**Recommendation:**
- Validate/sanitize the address string before geocoding (e.g., strip control characters, limit length — already done by Pydantic `max_length=500`)
- This is low risk given the existing Pydantic constraints

---

#### L-3: Debug-Level Logging in Production

**Location:** `src/api.py`  
**Impact:** Request logging includes user addresses, coordinates, and prediction values. While useful for debugging, this could be a privacy concern under GDPR/CCPA if logs are retained.

**Evidence:**
```python
logger.info(
    f"[{request_id}] address={req.address!r} lat={geo.lat:.4f} lng={geo.lng:.4f} "
    f"comps={len(comps)} revenue=${annual_revenue:,.0f} conf={confidence.level} ..."
)
```

**Recommendation:**
- Hash or truncate addresses in logs
- Ensure log retention policies comply with applicable privacy regulations
- Consider using structured logging with PII redaction

---

#### L-4: No Security Headers

**Location:** `src/api.py`  
**Impact:** The application does not set security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`).

**Recommendation:**
```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
```

---

## Dependency Analysis

| Package | Version | Status |
|---------|---------|--------|
| fastapi | 0.138.1 | ✅ Current |
| uvicorn | 0.49.0 | ✅ Current |
| pydantic | 2.13.4 | ✅ Current |
| xgboost | 3.3.0 | ✅ Current |
| lightgbm | 4.6.0 | ✅ Current |
| scikit-learn | 1.9.0 | ✅ Current |
| scipy | 1.18.0 | ✅ Current |
| pandas | 3.0.3 | ✅ Current |
| numpy | 2.4.6 | ✅ Current |
| geopy | 2.4.1 | ✅ Current |
| cachetools | 7.1.4 | ✅ Current |
| jinja2 | 3.1.4 | ✅ Current |
| joblib | 1.5.3 | ✅ Current |

**Note:** All pinned versions appear current as of the audit date. However:
- No `pip-audit` or `safety` check is integrated into CI/CD
- No lock file (`requirements.lock` or `poetry.lock`) — transitive dependencies are unpinned

---

## What's Done Well ✅

1. **Pydantic validation** — Input schemas enforce type safety, length limits, and value ranges at the framework level
2. **Structured error handling** — Custom exceptions with clean HTTP responses; generic handler catches unhandled errors without leaking stack traces
3. **Secrets via environment variables** — `MAPBOX_TOKEN` loaded from `os.getenv()`, not hardcoded
4. **Input bounds checking** — NYC bounding box validation, nightly rate ranges, bedroom/bathroom limits
5. **Docker layer caching** — Requirements installed before copying source (good build practice)
6. **Health/readiness endpoints** — Proper separation of health (`/v1/health`) and readiness (`/v1/ready`)

---

## Summary Matrix

| # | Finding | Severity | Category |
|---|---------|----------|----------|
| C-1 | No authentication/authorization | Critical | API Security |
| C-2 | No rate limiting | Critical | API Security |
| H-1 | XSS via innerHTML | High | Input Validation |
| H-2 | Container runs as root | High | Container Security |
| H-3 | Unsafe joblib deserialization | High | Data Integrity |
| M-1 | No CORS configuration | Medium | Configuration |
| M-2 | Batch error leaks exception names | Medium | Error Handling |
| M-3 | Mapbox token in URL path | Medium | Data Exposure |
| M-4 | No request body size limit | Medium | Denial of Service |
| M-5 | Geocoding cache poisoning | Medium | Denial of Service |
| L-1 | Model info endpoint exposes internals | Low | Data Exposure |
| L-2 | SSRF risk via Nominatim (mitigated) | Low | Input Validation |
| L-3 | PII in logs | Low | Data Exposure |
| L-4 | No security headers | Low | Configuration |

---

## Priority Remediation Order

1. **C-1 + C-2** — Authentication + rate limiting (blocks abuse)
2. **H-2** — Non-root container user (quick Dockerfile fix)
3. **H-1** — Sanitize DOM output (quick JS fix)
4. **H-3** — Model integrity verification
5. **M-1 through M-5** — Address as part of hardening sprint
6. **L-1 through L-4** — Address during next security review cycle
