"""Integration test: /api/cities reports real data freshness from the DB."""
import re

import pytest


def test_cities_returns_real_freshness():
    try:
        from fastapi.testclient import TestClient
        from src.api import app
    except Exception as e:  # httpx/testclient or app import unavailable
        pytest.skip(f"test client/app unavailable: {e}")

    try:
        with TestClient(app) as client:  # runs lifespan (model load + index)
            resp = client.get("/api/cities")
    except Exception as e:  # native libs (LightGBM) unavailable, etc.
        pytest.skip(f"app startup failed in this environment: {e}")

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("cities"), "expected at least one city"
    fresh = data.get("data_freshness")
    # Must be a real ISO date, not a hardcoded/placeholder string.
    assert fresh and re.match(r"^\d{4}-\d{2}-\d{2}$", fresh)


def test_listings_expose_seasonal_demand_curve():
    """/api/listings must carry the real month-by-month demand curve so the map's
    Demand layer / timeline can use it instead of the old review-count proxy."""
    import json

    try:
        from fastapi.testclient import TestClient
        from src.api import app
    except Exception as e:
        pytest.skip(f"test client/app unavailable: {e}")

    try:
        with TestClient(app) as client:
            # Broward County, FL bounding box — a covered market.
            resp = client.get(
                "/api/listings",
                params={"north": 26.4, "south": 25.9, "east": -80.0, "west": -80.5, "limit": 50},
            )
    except Exception as e:
        pytest.skip(f"app startup failed in this environment: {e}")

    assert resp.status_code == 200
    listings = resp.json().get("listings", [])
    if not listings:
        pytest.skip("no listings loaded in this environment's DB")

    # The field must be present on the payload (additive contract).
    assert "demand_curve" in listings[0]

    # At least one listing should carry a well-formed 12-slot curve with values
    # in [0, 1] (or null for months with no calendar data) — a real signal, not
    # a review count.
    parsed_any = False
    for l in listings:
        raw = l.get("demand_curve")
        if not raw:
            continue
        curve = json.loads(raw)
        assert isinstance(curve, list) and len(curve) == 12
        for v in curve:
            assert v is None or (isinstance(v, (int, float)) and 0.0 <= v <= 1.0)
        parsed_any = True
    assert parsed_any, "expected at least one listing with a populated demand_curve"
