"""Input validation and NYC bounds checking."""
from .config import settings
from .exceptions import InvalidInputError, OutsideCoverageError


def validate_input(address: str, bedrooms: int, bathrooms: int, accommodates: int, nightly_rate: float):
    """Validate all input parameters."""
    if not address or not address.strip():
        raise InvalidInputError("Address is required")

    if bedrooms < 0 or bedrooms > 10:
        raise InvalidInputError("Bedrooms must be between 0 and 10")

    if bathrooms < 0 or bathrooms > 10:
        raise InvalidInputError("Bathrooms must be between 0 and 10")

    if accommodates < 1 or accommodates > 20:
        raise InvalidInputError("Accommodates must be between 1 and 20")

    if nightly_rate <= 0:
        raise InvalidInputError("Nightly rate must be positive")

    warnings = []
    if nightly_rate < settings.NIGHTLY_RATE_MIN:
        warnings.append(f"${nightly_rate:.0f}/night is below typical NYC range (${settings.NIGHTLY_RATE_MIN:.0f}+)")
    if nightly_rate > settings.NIGHTLY_RATE_MAX:
        warnings.append(f"${nightly_rate:.0f}/night is above typical NYC range. Prediction may be unreliable.")

    return warnings


def in_nyc_bounds(lat: float, lng: float) -> bool:
    """True if the coordinates fall inside the NYC bounding box.

    Used to route requests: NYC uses the trained ML model, everywhere else
    falls through to the comp-based estimate over the market DB.
    """
    return (settings.NYC_LAT_MIN <= lat <= settings.NYC_LAT_MAX
            and settings.NYC_LNG_MIN <= lng <= settings.NYC_LNG_MAX)


def validate_nyc_bounds(lat: float, lng: float):
    """Check if coordinates are within NYC bounding box."""
    if not (settings.NYC_LAT_MIN <= lat <= settings.NYC_LAT_MAX):
        raise OutsideCoverageError(
            f"Address is outside NYC (lat={lat:.4f}, expected {settings.NYC_LAT_MIN}-{settings.NYC_LAT_MAX})"
        )
    if not (settings.NYC_LNG_MIN <= lng <= settings.NYC_LNG_MAX):
        raise OutsideCoverageError(
            f"Address is outside NYC (lng={lng:.4f}, expected {settings.NYC_LNG_MIN}-{settings.NYC_LNG_MAX})"
        )
