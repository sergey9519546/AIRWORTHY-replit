"""Integration tests: per-API-key rate limiting on /v1/estimate & /v1/batch.

These guard the mechanism that throttles a noisy or leaked partner key without
affecting other partners:

  * a partner key with a bespoke budget starts returning 429 after its limit,
    while a *different* partner key on the same client keeps succeeding;
  * the shared public BROWSER_API_KEY buckets per-IP (not per-key), so it is
    never given a bespoke per-key budget;
  * a request with no key is rejected with 401.

They exercise the real app (rate-limit decorators, key_func, dynamic limit
providers, verify_api_key) end to end via TestClient. Only `_do_estimate` is
patched out, so no real geocoding / model inference happens.

Because API_KEYS / BROWSER_API_KEY / API_KEY_RATE_LIMITS are read from the
environment at import time, each test sets the env it needs and reloads
`src.api`. Reloading also builds a fresh Limiter with fresh in-memory counters,
so rate-limit state never bleeds between tests.

The rate-limit path (key_func, dynamic limit providers, verify_api_key) never
needs the ML model, the comp index, the training CSV, or amenity calibration —
those only matter inside `_do_estimate`, which we stub out. So we neutralize the
heavy/native startup steps in the app's lifespan, letting these guard tests run
deterministically (and *fail* on real regressions) without depending on native
LightGBM libs or data files being present.
"""
import importlib

import pandas as pd


def _load_app(monkeypatch, env):
    """Reload src.api with `env` applied, neutralize heavy startup, and stub
    out `_do_estimate`. Returns the reloaded module (use its `.app`).

    An import or startup failure here is a genuine regression and is allowed to
    surface as a test error rather than being swallowed into a skip.
    """
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    import src.api as api
    importlib.reload(api)
    from src.schemas import (
        EstimateResponse, ConfidenceResponse, MarketResponse,
    )

    # Neutralize the lifespan's heavy/native startup so TestClient boots
    # deterministically. None of this is exercised by the rate-limit path
    # (`_do_estimate` is stubbed), so replacing them with no-ops keeps the tests
    # focused on the throttling behavior instead of model/data availability.
    monkeypatch.setattr(api, "load_model", lambda *a, **k: None)
    monkeypatch.setattr(api, "build_index", lambda *a, **k: None)
    monkeypatch.setattr(api, "warm_calibration", lambda *a, **k: None)
    monkeypatch.setattr(api.pd, "read_csv", lambda *a, **k: pd.DataFrame())

    async def _fake_estimate(req):
        # A minimal but schema-valid response so a *successful* call returns 200
        # without touching geocoding, the DB, or the model.
        return EstimateResponse(
            address=req.address,
            lat=26.1,
            lng=-80.1,
            annual_revenue=50000.0,
            airworthy_score=80,
            airworthy_verdict="Airworthy",
            airworthy_reason="test stub",
            confidence=ConfidenceResponse(
                level="high", revenue_lower=40000.0, revenue_upper=60000.0, cv=0.1,
            ),
            comps=[],
            market=MarketResponse(
                borough="Test", median_revenue=50000.0, median_price=200.0,
                active_listings=10,
            ),
            disclaimer="test",
            data_source="test",
            model_version="test",
            data_freshness="2026-01-01",
        )

    monkeypatch.setattr(api, "_do_estimate", _fake_estimate)
    return api


_BODY = {"address": "123 Test St, Fort Lauderdale, FL", "bedrooms": 2}


def _client(api):
    from fastapi.testclient import TestClient
    client = TestClient(api.app)
    client.__enter__()  # run lifespan (heavy startup steps are stubbed above)
    return client


def test_bespoke_per_key_budget_isolated_between_partners(monkeypatch):
    """partnerA has a 2/minute budget: its 3rd call in the window is 429, but
    partnerB (default budget) on the *same* client is unaffected — proving the
    limit buckets per key, not per IP/connection."""
    api = _load_app(monkeypatch, {
        "API_KEYS": "partnerA,partnerB",
        "API_KEY_RATE_LIMITS": "partnerA=2/minute",
        "RATE_LIMIT_ESTIMATE": "30/minute",
        "REPLIT_DEPLOYMENT": None,
    })
    client = _client(api)
    try:
        a = {"X-API-Key": "partnerA"}
        b = {"X-API-Key": "partnerB"}

        # partnerA: first two succeed, third is throttled.
        assert client.post("/v1/estimate", json=_BODY, headers=a).status_code == 200
        assert client.post("/v1/estimate", json=_BODY, headers=a).status_code == 200
        r3 = client.post("/v1/estimate", json=_BODY, headers=a)
        assert r3.status_code == 429, r3.text
        assert r3.json()["error"] == "rate_limit_exceeded"

        # partnerB shares the same client (same IP) but has its own bucket:
        # it must still succeed well past partnerA's exhausted 2/minute.
        for _ in range(3):
            assert client.post("/v1/estimate", json=_BODY, headers=b).status_code == 200
    finally:
        client.__exit__(None, None, None)


def test_bespoke_budget_reported_in_ratelimit_header(monkeypatch):
    """The bespoke per-key budget is what shows up in X-RateLimit-Limit, so a
    partner can see its own (not the default) ceiling."""
    api = _load_app(monkeypatch, {
        "API_KEYS": "partnerA,partnerB",
        "API_KEY_RATE_LIMITS": "partnerA=2/minute",
        "RATE_LIMIT_ESTIMATE": "30/minute",
        "REPLIT_DEPLOYMENT": None,
    })
    client = _client(api)
    try:
        ra = client.post("/v1/estimate", json=_BODY, headers={"X-API-Key": "partnerA"})
        assert ra.status_code == 200
        assert ra.headers.get("X-RateLimit-Limit") == "2"

        rb = client.post("/v1/estimate", json=_BODY, headers={"X-API-Key": "partnerB"})
        assert rb.status_code == 200
        # partnerB has no bespoke budget -> default 30/minute.
        assert rb.headers.get("X-RateLimit-Limit") == "30"
    finally:
        client.__exit__(None, None, None)


def test_browser_key_buckets_per_ip_not_per_key(monkeypatch):
    """The shared public BROWSER_API_KEY must NOT get its own per-key bucket:
    verify_api_key leaves request.state.api_key None for it, so it falls back to
    per-IP limiting. A bespoke API_KEY_RATE_LIMITS entry naming the browser key
    is therefore ignored (the key: tag is never produced for it)."""
    api = _load_app(monkeypatch, {
        "API_KEYS": "partnerA",
        "BROWSER_API_KEY": "browserpub",
        # Even if someone tries to give the browser key a tiny bespoke budget,
        # it can't take effect because browser traffic is IP-bucketed.
        "API_KEY_RATE_LIMITS": "browserpub=1/minute",
        "RATE_LIMIT_ESTIMATE": "30/minute",
        "REPLIT_DEPLOYMENT": None,
    })
    client = _client(api)
    try:
        h = {"X-API-Key": "browserpub"}
        # If the browser key were keyed like a partner, the 1/minute bespoke
        # budget would 429 the 2nd call. It buckets per-IP at the 30/minute
        # default instead, so several calls all succeed.
        for _ in range(5):
            r = client.post("/v1/estimate", json=_BODY, headers=h)
            assert r.status_code == 200, r.text
        # Header reflects the per-IP default, not the ignored bespoke "1".
        assert r.headers.get("X-RateLimit-Limit") == "30"
    finally:
        client.__exit__(None, None, None)


def test_missing_key_rejected_in_production(monkeypatch):
    """With keys configured (production posture), a request with no X-API-Key is
    401 — there's no anonymous exemption to rate-limit around."""
    api = _load_app(monkeypatch, {
        "API_KEYS": "partnerA",
        "REPLIT_DEPLOYMENT": "1",
        "API_KEY_RATE_LIMITS": None,
    })
    client = _client(api)
    try:
        r = client.post("/v1/estimate", json=_BODY)
        assert r.status_code == 401, r.text
    finally:
        client.__exit__(None, None, None)


def test_batch_bespoke_per_key_budget(monkeypatch):
    """The same per-key budgeting applies to /v1/batch via its own
    API_KEY_BATCH_RATE_LIMITS override, independent of the estimate budget."""
    api = _load_app(monkeypatch, {
        "API_KEYS": "partnerA,partnerB",
        "API_KEY_BATCH_RATE_LIMITS": "partnerA=1/minute",
        "RATE_LIMIT_BATCH": "5/minute",
        "REPLIT_DEPLOYMENT": None,
    })
    client = _client(api)
    try:
        a = {"X-API-Key": "partnerA"}
        b = {"X-API-Key": "partnerB"}
        payload = [_BODY]

        assert client.post("/v1/batch", json=payload, headers=a).status_code == 200
        r2 = client.post("/v1/batch", json=payload, headers=a)
        assert r2.status_code == 429, r2.text

        # partnerB keeps its own (default) batch budget.
        assert client.post("/v1/batch", json=payload, headers=b).status_code == 200
    finally:
        client.__exit__(None, None, None)
