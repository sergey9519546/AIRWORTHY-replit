"""Unit tests for src.property_photo: static-map/placeholder filtering."""
from src.property_photo import _extract_image, _pick_photo


def _result(url, image=None):
    return {"url": url, "metadata": {"ogImage": image} if image else {}}


def test_extract_image_skips_google_static_map():
    item = _result(
        "https://www.zillow.com/homedetails/123-main-st",
        "https://maps.googleapis.com/maps/api/staticmap?center=40,-74&zoom=15",
    )
    assert _extract_image(item) is None


def test_extract_image_skips_placeholder():
    item = _result(
        "https://www.zillow.com/homedetails/123-main-st",
        "https://www.zillow.com/static/images/MissingPhotography.png",
    )
    assert _extract_image(item) is None


def test_extract_image_accepts_real_photo():
    item = _result(
        "https://www.zillow.com/homedetails/123-main-st",
        "https://photos.zillowstatic.com/fp/abc123-uncropped.jpg",
    )
    assert _extract_image(item) == "https://photos.zillowstatic.com/fp/abc123-uncropped.jpg"


def test_pick_photo_falls_through_when_top_result_is_only_a_map():
    # Zillow (top-priority) has only a static-map screenshot; Redfin (lower
    # priority) has a real photo. Should fall through to the real photo.
    results = [
        _result(
            "https://www.zillow.com/homedetails/123-main-st",
            "https://maps.googleapis.com/maps/api/staticmap?center=40,-74",
        ),
        _result(
            "https://www.redfin.com/home/123-main-st",
            "https://ssl.cdn-redfin.com/photo/123/genLarge.jpg",
        ),
    ]
    photo = _pick_photo(results)
    assert photo is not None
    assert photo.photo_url == "https://ssl.cdn-redfin.com/photo/123/genLarge.jpg"
    assert photo.source_site == "Redfin"


def test_pick_photo_returns_none_when_all_results_are_maps():
    results = [
        _result(
            "https://www.zillow.com/homedetails/123-main-st",
            "https://maps.googleapis.com/maps/api/staticmap?center=40,-74",
        ),
    ]
    assert _pick_photo(results) is None
