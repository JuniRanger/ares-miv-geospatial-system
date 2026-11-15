"""Terrain and elevation response schemas."""

from pydantic import BaseModel

from app.schemas.common import DataAvailability


class ElevationResponse(BaseModel):
    """Elevation response; measurement is null until validated data is available."""

    latitude: float
    longitude: float
    elevation_m: float | None
    data_available: bool


class TerrainResponse(BaseModel):
    """Terrain measurements and per-measurement availability metadata."""

    latitude: float
    longitude: float
    elevation_m: float | None
    slope_deg: float | None
    roughness_m: float | None
    thermal_inertia: float | None
    traversable: bool | None
    radiation: float | None
    data_availability: DataAvailability
