"""Custom exceptions."""


class GeocodingError(Exception):
    """Address could not be geocoded."""
    pass


class OutsideCoverageError(Exception):
    """Address is outside NYC coverage area."""
    pass


class InsufficientCompsError(Exception):
    """Not enough comparable listings found."""
    pass


class ModelNotReadyError(Exception):
    """Model is not loaded."""
    pass


class InvalidInputError(Exception):
    """Invalid input parameters."""
    pass
