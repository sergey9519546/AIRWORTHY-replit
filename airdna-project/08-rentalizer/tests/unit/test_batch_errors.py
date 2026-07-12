"""Regression test: batch endpoint preserves specific error reasons."""
from src.api import _BATCH_ERROR_CODES
from src.exceptions import GeocodingError, OutsideCoverageError, InvalidInputError


def test_batch_error_codes_cover_user_facing_exceptions():
    """Each user-facing typed exception maps to a stable, specific code
    (so batch items don't collapse to a generic 'estimation_failed')."""
    assert _BATCH_ERROR_CODES[GeocodingError] == "geocoding_failed"
    assert _BATCH_ERROR_CODES[OutsideCoverageError] == "outside_coverage_area"
    assert _BATCH_ERROR_CODES[InvalidInputError] == "invalid_input"
