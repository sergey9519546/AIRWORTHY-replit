# API Design Audit — Rentalizer

**Auditor:** Senior API Designer  
**Date:** 2026-06-29  
**Files reviewed:** `src/api.py`, `src/schemas.py`, `src/config.py`, `src/validation.py`, `src/exceptions.py`

---

## Executive Summary

The API is functional and well-structured for an MVP, but has **significant gaps** that would block production deployment: no rate limiting, no CORS, no pagination on batch, inconsistent error schemas, missing OpenAPI docs configuration, and a few REST design violations. Several of these are trivial to fix.

**Severity counts:** 🔴 Critical (3) · 🟡 Major (5) · 🔵 Minor (4)

---

## 1. RESTful Design

### ✅ What's Good
- `POST /v1/estimate` is correct — this is a computation, not a resource CRUD.
- `GET /v1/health` and `GET /v1/ready` follow health-check conventions.
- `GET /v1/model/info` and `GET /v1/credits` are read-only resources — correct method.

### 🟡 `POST /v1/batch` returns 200 even when some items fail

The batch endpoint catches per-item exceptions and stuffs them into the response array. The HTTP status is always 200. This violates the principle that the status code should reflect the overall outcome.

```python
# Current — always 200
results.append({"error": type(e).__name__, "detail": str(e)})
return results

# Better: return 207 Multi-Status with per-item status codes
# Or at minimum: return 400 if ALL fail, 200 if all succeed, 207 for partial
```

**Fix:** Use `207 Multi-Status` when there's a mix of success/failure:

```python
@app.post("/v1/batch")
async def batch_estimate(requests: list[EstimateRequest]):
    if len(requests) > settings.MAX_BATCH:
        return JSONResponse(status_code=413, content={
            "error": "batch_too_large",
            "detail": f"Maximum batch size is {settings.MAX_BATCH}",
        })

    results = []
    has_error = False
    has_success = False

    for req in requests:
        try:
            result = await estimate(req)
            results.append({"status": 200, "data": result.model_dump()})
            has_success = True
        except (GeocodingError, OutsideCoverageError, InvalidInputError) as e:
            results.append({"status": 422, "error": type(e).__name__, "detail": str(e)})
            has_error = True
        except Exception as e:
            results.append({"status": 500, "error": "internal_error", "detail": str(e)})
            has_error = True

    status = 200
    if has_error and has_success:
        status = 207  # Multi-Status
    elif has_error:
        status = 422  # All failed

    return JSONResponse(status_code=status, content={"results": results})
```

### 🟡 Batch endpoint schema mismatch

The batch endpoint declares no `response_model`. The response is a bare JSON array with no wrapper. Every other endpoint uses a response model. This means:
- No automatic OpenAPI response schema documentation.
- Inconsistent envelope — other endpoints return objects, this returns an array.
- The error items in the array don't match `ErrorResponse` schema.

**Fix:** Define a `BatchResponse` schema:

```python
class BatchItemResult(BaseModel):
    status: int
    data: EstimateResponse | None = None
    error: str | None = None
    detail: str | None = None

class BatchResponse(BaseModel):
    results: list[BatchItemResult]
```

### 🔵 `GET /v1/ready` should use `response_model`

```python
# Current
@app.get("/v1/ready")
async def ready():
    return {"model_loaded": m is not None, "index_loaded": t is not None}

# Fix
class ReadyResponse(BaseModel):
    model_loaded: bool
    index_loaded: bool

@app.get("/v1/ready", response_model=ReadyResponse)
```

---

## 2. Response Format Consistency

### 🟡 Missing `request_id` in responses

The code generates `request_id = str(uuid.uuid4())[:8]` but never returns it. This makes debugging impossible when users report issues.

**Fix:**

```python
class EstimateResponse(BaseModel):
    request_id: str  # Add this
    address: str
    lat: float
    # ... rest unchanged
```

### 🟡 No standard envelope

Some endpoints return raw objects, the batch returns an array, errors use a different shape than `ErrorResponse` (some have `suggestion`, some don't). A consistent envelope would be:

```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "request_id": "a1b2c3d4",
    "processing_time_ms": 342
  }
}
```

Even if you don't adopt a full envelope, at minimum: **always include `request_id` in every response**.

### 🔵 `annual_revenue` type inconsistency

`annual_revenue` is `round(annual_revenue, 0)` which returns a `float` (e.g., `45000.0`). If it's always rounded to zero decimals, declare it as `int` in the schema or use `ge=0` constraint. Consumers will be confused by `45000.0` vs `45000`.

---

## 3. Error Handling

### ✅ What's Good
- Custom exception hierarchy (`GeocodingError`, `OutsideCoverageError`, etc.)
- Structured JSON error responses with `error`, `detail`, `suggestion` fields.
- Generic catch-all returns 500 with safe message (no stack trace leaked).

### 🔴 `InsufficientCompsError` and `ModelNotReadyError` have no handlers

These exceptions are defined but never registered with `@app.exception_handler()`. If they're raised, the generic handler catches them, but:
- `InsufficientCompsError` should return 422 with a clear message, not a generic 500.
- `ModelNotReadyError` should return 503 Service Unavailable.

```python
@app.exception_handler(InsufficientCompsError)
async def insufficient_comps_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "error": "insufficient_comps",
        "detail": str(exc),
        "suggestion": "Try an address in a more densely listed area of NYC.",
    })

@app.exception_handler(ModelNotReadyError)
async def model_not_ready_handler(request, exc):
    return JSONResponse(status_code=503, content={
        "error": "model_not_ready",
        "detail": "The prediction model is still loading. Please try again in a few seconds.",
    })
```

### 🔴 Geocoding failures from `geocode()` are unhandled

If `geocode()` raises an unexpected exception (network timeout, Mapbox API error, invalid token), it's not a `GeocodingError` — it bubbles to the generic handler as a 500. The geocoding wrapper should catch all Mapbox errors and re-raise as `GeocodingError`.

### 🔵 Error responses don't match `ErrorResponse` schema

The `ErrorResponse` schema has a `suggestion` field with `default=""`, but `geocoding_handler` and `coverage_handler` set it while `invalid_input_handler` omits it. Since the schema has a default, this technically works, but the `ErrorResponse` schema is never used as a `response_model` anywhere — it's dead code.

**Fix:** Use it:

```python
@app.exception_handler(GeocodingError)
async def geocoding_handler(request, exc):
    resp = ErrorResponse(
        error="geocoding_failed",
        detail=str(exc),
        suggestion="Try a more specific address...",
    )
    return JSONResponse(status_code=422, content=resp.model_dump())
```

---

## 4. Input Validation

### ✅ What's Good
- Pydantic `Field` constraints on `EstimateRequest` (min/max on bedrooms, bathrooms, etc.)
- Separate validation module for business rules.
- NYC bounds check after geocoding.

### 🟡 `property_type` is accepted but never used

`EstimateRequest` declares `property_type: str = Field(default="Entire home/apt")` but it's never referenced in `estimate()`. This is confusing — users might think it affects the prediction.

**Options:**
1. Actually use it in feature engineering.
2. Remove it from the schema.
3. Accept it but document it's unused (bad UX).

### 🟡 `validate_input` is redundant with Pydantic

`validate_input()` manually checks `bedrooms < 0 or bedrooms > 10` — but Pydantic already enforces `Field(ge=0, le=10)`. If the request reaches `estimate()`, those values are already valid. The manual checks will never trigger.

**Fix:** Remove the duplicate range checks. Keep only the business-logic warnings:

```python
def validate_input(address: str, bedrooms: int, bathrooms: int,
                   accommodates: int, nightly_rate: float):
    warnings = []
    if nightly_rate < settings.NIGHTLY_RATE_MIN:
        warnings.append(f"${nightly_rate:.0f}/night is below typical NYC range")
    if nightly_rate > settings.NIGHTLY_RATE_MAX:
        warnings.append(f"${nightly_rate:.0f}/night is above typical NYC range")
    return warnings
```

### 🔵 `address` validation is weak

`min_length=1` allows `" "` (single space). The `validate_input` function checks `not address.strip()` but that's a Pydantic bypass — Pydantic passes `" "` through and the manual check catches it. Use a Pydantic validator instead:

```python
from pydantic import field_validator

class EstimateRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)

    @field_validator("address")
    @classmethod
    def strip_address(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Address cannot be blank")
        return v
```

---

## 5. Rate Limiting

### 🔴 Not implemented at all

There is zero rate limiting. The `/v1/estimate` endpoint calls an external geocoding API (Mapbox), runs ML inference, and queries a comp index — all expensive. Any client can hammer this at 1000 req/s.

**Impact:**
- Mapbox API costs explode.
- Server resources exhausted.
- Single tenant can DoS the service.

**Fix — minimum viable:**

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/v1/estimate", response_model=EstimateResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def estimate(request: Request, req: EstimateRequest):
    ...

@app.post("/v1/batch")
@limiter.limit("5/minute")  # Expensive — stricter limit
async def batch_estimate(request: Request, requests: list[EstimateRequest]):
    ...
```

Also add rate limit headers to responses:

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1719558000
```

---

## 6. Pagination

### 🟡 Batch endpoint needs it (or at least a size limit response)

The batch endpoint caps at 20 (`MAX_BATCH`), which is fine. But the response has no indication of the limit, how many were processed, or whether truncation occurred.

**Fix:** Wrap in a proper response:

```python
class BatchResponse(BaseModel):
    total: int
    processed: int
    results: list[BatchItemResult]
```

For the comps list, `comps[:5]` is hardcoded. This should be configurable:

```python
class EstimateRequest(BaseModel):
    # ... existing fields
    max_comps: int = Field(ge=1, le=20, default=5)
```

---

## 7. Versioning

### ✅ `/v1/` prefix is correct

The versioning approach is fine. But:

### 🔵 No version negotiation or deprecation strategy

- What happens when v2 ships? Will v1 be maintained?
- No `Deprecation` header for old versions.
- No documentation of version lifecycle.

**Recommendation:** Document the versioning policy in the OpenAPI description:

```python
app = FastAPI(
    title="Rentalizer",
    description=(
        "Short-term rental revenue estimation tool.\n\n"
        "## Versioning\n"
        "This API follows [calendar versioning](https://calver.org/). "
        "The `/v1/` prefix will be maintained for at least 12 months after "
        "a `/v2/` release. Deprecated endpoints return a `Deprecation` header."
    ),
)
```

---

## 8. CORS

### 🔴 Not configured

The API serves a web UI (`/` returns HTML) and likely needs to be called from a browser frontend. There is **no CORS middleware**. Any browser-based client on a different origin will be blocked.

**Fix:**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Dev
        "https://rentalizer.example.com",  # Production
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight for 24h
)
```

**Do NOT use `allow_origins=["*"]`** in production — it defeats the purpose of CORS entirely.

---

## 9. Content Negotiation

### 🔵 Not implemented

The API always returns `application/json` (FastAPI default) and never checks `Accept` headers. For a JSON API this is **acceptable** but not ideal:

- If a client sends `Accept: text/xml`, they get JSON with a 200 status instead of `406 Not Acceptable`.
- The `/` endpoint returns HTML but doesn't set `Content-Type` explicitly (Jinja2 handles it).

**Recommendation:** For v1, this is fine. For v2, add explicit content negotiation if you support multiple formats.

---

## 10. API Documentation

### 🟡 OpenAPI is auto-generated but unconfigured

FastAPI generates `/docs` (Swagger) and `/redoc` automatically, which is good. But:

- No `tags` on endpoints — they all appear in a single "default" group.
- No `description` on individual endpoints beyond the docstring.
- No example request/response bodies.
- No `response_model` on batch or ready endpoints = no schema docs.
- `ErrorResponse` is defined but never referenced in OpenAPI `responses`.

**Fix — add tags and examples:**

```python
@app.post(
    "/v1/estimate",
    response_model=EstimateResponse,
    tags=["estimation"],
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Model not ready"},
    },
    summary="Estimate annual revenue for a property",
    description="Geocodes the address, finds comparable listings, "
                "and predicts annual short-term rental revenue.",
)
async def estimate(req: EstimateRequest):
    ...

@app.post("/v1/batch", tags=["estimation"])
async def batch_estimate(...):
    ...

@app.get("/v1/health", tags=["operations"])
async def health():
    ...

@app.get("/v1/ready", tags=["operations"])
async def ready():
    ...

@app.get("/v1/model/info", tags=["operations"])
async def model_info():
    ...

@app.get("/v1/credits", tags=["metadata"])
async def credits():
    ...
```

**Add request examples to schemas:**

```python
class EstimateRequest(BaseModel):
    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        json_schema_extra={"examples": ["350 5th Ave, New York, NY 10118"]}
    )
    bedrooms: int = Field(ge=0, le=10, default=1)
    # ...
```

---

## Summary of Action Items

| # | Severity | Issue | Fix Effort |
|---|----------|-------|------------|
| 1 | 🔴 | No rate limiting | 30 min |
| 2 | 🔴 | No CORS middleware | 10 min |
| 3 | 🔴 | Missing exception handlers for `InsufficientCompsError`, `ModelNotReadyError` | 10 min |
| 4 | 🟡 | Batch endpoint: no `response_model`, always 200, no per-item status | 45 min |
| 5 | 🟡 | `request_id` generated but not returned | 5 min |
| 6 | 🟡 | `property_type` accepted but unused | 5 min (remove or use) |
| 7 | 🟡 | `validate_input` duplicates Pydantic checks | 10 min |
| 8 | 🟡 | OpenAPI: no tags, no examples, no error response models | 30 min |
| 9 | 🔵 | `address` validation allows whitespace-only | 5 min |
| 10 | 🔵 | `annual_revenue` returns float instead of int | 5 min |
| 11 | 🔵 | `GET /v1/ready` missing `response_model` | 5 min |
| 12 | 🔵 | `ErrorResponse` schema defined but never used | 10 min |

---

## Overall Verdict

**Grade: C+** — Solid MVP, not production-ready.

The core logic is well-organized (separate validation, exceptions, schemas). The Pydantic usage is good. But the API surface has too many rough edges: no rate limiting is a billing bomb waiting to happen, no CORS means the frontend is locked out, and the error handling has real gaps. The good news: most of this is fixable in a single focused session.

Priority order: Rate limiting → CORS → Exception handlers → Batch response → OpenAPI docs.
