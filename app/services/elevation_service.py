"""Interface for reading elevation from validated raster products."""

from app.schemas.terrain import ElevationResponse


def get_elevation(latitude: float, longitude: float) -> ElevationResponse:
    """Read elevation and source availability at a named coordinate."""
    raise NotImplementedError("Elevation lookup is not implemented.")
