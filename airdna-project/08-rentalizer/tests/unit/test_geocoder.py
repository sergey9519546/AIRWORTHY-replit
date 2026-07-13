"""Regression tests for the geocoder.

Covers the listings-database fallback: when a user pastes an Airbnb listing
title into the address box and the external geocoders can't resolve it, the
local listings table should provide the stored lat/lng.
"""
import os
import sqlite3
import tempfile

import pytest

from src import geocoder
from src.exceptions import GeocodingError


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch):
    geocoder._cache.clear()
    yield
    geocoder._cache.clear()


@pytest.fixture
def listings_db_path():
    """Create a temporary listings database with a single listing row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE listings (
                id INTEGER PRIMARY KEY,
                name TEXT,
                city TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL
            )
            """
        )
        conn.execute(
            "INSERT INTO listings (id, name, city, state, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "Seascape Ocean View Hideaway 760", "santa-cruz-county", "ca", 36.9569248, -121.8878827),
        )
        conn.commit()
    finally:
        conn.close()

    yield path

    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def test_listings_db_fallback_resolves_listing_name(monkeypatch, listings_db_path):
    """A listing title that external geocoders miss should resolve from the DB."""
    monkeypatch.setattr(geocoder, "_db_path", lambda: listings_db_path)
    monkeypatch.setattr(geocoder, "_geocode_mapbox", lambda address: None)
    monkeypatch.setattr(geocoder, "_geocode_nominatim", lambda address: None)

    result = geocoder.geocode("Seascape Ocean View Hideaway 760")

    assert result.source == "listings_db"
    assert result.lat == pytest.approx(36.9569248)
    assert result.lng == pytest.approx(-121.8878827)
    assert "Seascape Ocean View Hideaway 760" in result.display_name


def test_external_geocoder_wins_before_fallback(monkeypatch, listings_db_path):
    """If Mapbox/Nominatim succeed, the DB fallback is never used."""
    from src.config import settings
    monkeypatch.setattr(settings, "MAPBOX_TOKEN", "test-token")
    monkeypatch.setattr(geocoder, "_db_path", lambda: listings_db_path)
    monkeypatch.setattr(
        geocoder,
        "_geocode_mapbox",
        lambda address: geocoder.GeocodeResult(lat=40.0, lng=-74.0, display_name="Mapbox", source="mapbox"),
    )

    result = geocoder.geocode("Seascape Ocean View Hideaway 760")
    assert result.source == "mapbox"


def test_missing_listing_falls_back_to_error(monkeypatch, listings_db_path):
    """A listing title that is not in the DB should still raise GeocodingError."""
    monkeypatch.setattr(geocoder, "_db_path", lambda: listings_db_path)
    monkeypatch.setattr(geocoder, "_geocode_mapbox", lambda address: None)
    monkeypatch.setattr(geocoder, "_geocode_nominatim", lambda address: None)

    with pytest.raises(GeocodingError):
        geocoder.geocode("A listing that does not exist in the database")


def test_missing_db_file_returns_none(monkeypatch):
    """A non-existent DB path should be silently ignored, returning None."""
    monkeypatch.setattr(geocoder, "_db_path", lambda: "/tmp/nonexistent_rentalizer_listings.db")
    assert geocoder._geocode_listings_db("anything") is None
