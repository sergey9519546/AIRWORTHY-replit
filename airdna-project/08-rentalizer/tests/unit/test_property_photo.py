"""Unit tests for src.property_photo: static-map/placeholder filtering."""
from src.property_photo import _extract_gallery, _extract_image, _pick_photo


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


def _result_with_markdown(url, image, markdown):
    return {"url": url, "metadata": {"ogImage": image}, "markdown": markdown}


def test_extract_gallery_pulls_same_host_markdown_images():
    markdown = (
        "![Front of home](https://photos.zillowstatic.com/fp/front-uncropped.jpg)\n"
        "![Kitchen](https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg)\n"
        "![logo](https://photos.zillowstatic.com/fp/logo-icon.png)\n"
        "![other site](https://cdn.example.com/unrelated.jpg)\n"
    )
    gallery = _extract_gallery(
        {"url": "https://www.zillow.com/homedetails/123", "markdown": markdown},
        "https://photos.zillowstatic.com/fp/front-uncropped.jpg",
    )
    assert gallery == ["https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg"]


def test_extract_gallery_dedupes_and_skips_maps():
    markdown = (
        "![Kitchen](https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg)\n"
        "![Kitchen again](https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg)\n"
        "![Map](https://maps.googleapis.com/maps/api/staticmap?center=1,2)\n"
    )
    gallery = _extract_gallery(
        {"url": "https://www.zillow.com/homedetails/123", "markdown": markdown},
        "https://photos.zillowstatic.com/fp/front-uncropped.jpg",
    )
    assert gallery == ["https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg"]


def test_pick_photo_attaches_gallery_from_markdown():
    results = [
        _result_with_markdown(
            "https://www.zillow.com/homedetails/123-main-st",
            "https://photos.zillowstatic.com/fp/front-uncropped.jpg",
            "![Kitchen](https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg)",
        ),
    ]
    photo = _pick_photo(results)
    assert photo is not None
    assert photo.gallery == ["https://photos.zillowstatic.com/fp/kitchen-uncropped.jpg"]


def test_pick_photo_gallery_defaults_empty_without_markdown():
    photo = _pick_photo([
        _result(
            "https://www.zillow.com/homedetails/123-main-st",
            "https://photos.zillowstatic.com/fp/front-uncropped.jpg",
        ),
    ])
    assert photo is not None
    assert photo.gallery == []
