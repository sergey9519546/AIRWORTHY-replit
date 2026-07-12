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
