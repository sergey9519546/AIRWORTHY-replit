"""Unit tests for the Realie parcel-enrichment client.

Enrichment must be fail-open: an estimate should never break because Realie
is unconfigured, slow, erroring, or has no data for the address.
"""
import pytest

from src import realie_client
from src.config import settings


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def _clear_cache_and_key(monkeypatch):
    realie_client._cache.clear()
    monkeypatch.setattr(settings, "REALIE_API_KEY", "test-key")
    yield
    realie_client._cache.clear()


def test_no_api_key_returns_none_without_network_call(monkeypatch):
    monkeypatch.setattr(settings, "REALIE_API_KEY", "")

    def _boom(*a, **kw):
        raise AssertionError("should not call the network when no API key is set")

    monkeypatch.setattr(realie_client, "_fetch_parcel", _boom)
    assert realie_client.get_parcel(40.0, -74.0) is None


def test_successful_lookup_maps_fields_and_picks_nearest(monkeypatch):
    payload = {
        "properties": [
            {  # farther candidate
                "parcelId": "FAR-1",
                "location": {"type": "Point", "coordinates": [-74.01, 40.01]},
                "yearBuilt": 1950,
            },
            {  # exact match
                "parcelId": "NEAR-1",
                "location": {"type": "Point", "coordinates": [-74.0, 40.0]},
                "yearBuilt": 1998,
                "acres": 0.32,
                "buildingArea": 1800,
                "totalBedrooms": 3,
                "totalBathrooms": 2.5,
                "stories": 2,
                "garage": True,
                "pool": False,
                "constructionType": "F",
                "roofType": "P",
                "ownerName": "JOHN DOE",
                "totalMarketValue": 450000,
                "modelValue": 470000,
                "modelValueMin": 430000,
                "modelValueMax": 510000,
                "transferPrice": 400000,
                "transferDate": "2021-05-01",
            },
        ]
    }

    def _fake_get(url, params=None, headers=None, timeout=None):
        assert headers == {"Authorization": "test-key"}
        assert params["latitude"] == 40.0 and params["longitude"] == -74.0
        return _FakeResponse(200, payload)

    monkeypatch.setattr(realie_client, "_get_session", lambda: type("S", (), {"get": staticmethod(_fake_get)})())

    parcel = realie_client.get_parcel(40.0, -74.0)
    assert parcel is not None
    assert parcel.parcel_id == "NEAR-1"  # nearest to the query point, not first in list
    assert parcel.year_built == 1998
    assert parcel.bedrooms == 3
    assert parcel.bathrooms == 2.5
    assert parcel.avm_value == 470000
    assert parcel.owner_name == "JOHN DOE"
    assert parcel.source == "realie"


@pytest.mark.parametrize("status_code", [401, 403, 404, 500])
def test_error_responses_return_none_not_raise(monkeypatch, status_code):
    def _fake_get(*a, **kw):
        return _FakeResponse(status_code, {})

    monkeypatch.setattr(realie_client, "_get_session", lambda: type("S", (), {"get": staticmethod(_fake_get)})())
    assert realie_client.get_parcel(40.0, -74.0) is None


def test_network_exception_returns_none_not_raise(monkeypatch):
    def _fake_get(*a, **kw):
        raise TimeoutError("connection timed out")

    monkeypatch.setattr(realie_client, "_get_session", lambda: type("S", (), {"get": staticmethod(_fake_get)})())
    assert realie_client.get_parcel(40.0, -74.0) is None


def test_empty_properties_returns_none(monkeypatch):
    def _fake_get(*a, **kw):
        return _FakeResponse(200, {"properties": []})

    monkeypatch.setattr(realie_client, "_get_session", lambda: type("S", (), {"get": staticmethod(_fake_get)})())
    assert realie_client.get_parcel(40.0, -74.0) is None


def test_result_is_cached_after_first_lookup(monkeypatch):
    calls = {"n": 0}

    def _fake_get(*a, **kw):
        calls["n"] += 1
        return _FakeResponse(200, {"properties": [{
            "parcelId": "P1",
            "location": {"coordinates": [-74.0, 40.0]},
        }]})

    monkeypatch.setattr(realie_client, "_get_session", lambda: type("S", (), {"get": staticmethod(_fake_get)})())

    first = realie_client.get_parcel(40.0, -74.0)
    second = realie_client.get_parcel(40.0, -74.0)
    assert first == second
    assert calls["n"] == 1
