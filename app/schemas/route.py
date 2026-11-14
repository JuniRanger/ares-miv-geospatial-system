"""Route planning request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import WarningInfo
from app.schemas.coordinates import Coordinates


class RoutePreferences(BaseModel):
    """Route preferences from the documented API contract."""

    avoid_steep_slopes: bool = True
    avoid_rough_terrain: bool = True
    consider_thermal_data: bool = True


class RoutePlanRequest(BaseModel):
    """Origin, destination, and preferences for a future route calculation."""

    origin: Coordinates
    destination: Coordinates
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)


class GeoJSONLineString(BaseModel):
    """Route geometry with GeoJSON [longitude, latitude] coordinate order."""

    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]]


class ElevationProfilePoint(BaseModel):
    """Elevation sample along a route, nullable when source data is unavailable."""

    latitude: float
    longitude: float
    elevation_m: float | None


class RouteDataQuality(BaseModel):
    """Availability status of datasets used for route planning."""

    elevation: Literal["available", "partial", "unavailable"]
    roughness: Literal["available", "partial", "unavailable"]
    thermal: Literal["available", "partial", "unavailable"]


class RouteResponse(BaseModel):
    """Completed route response contract; no such response is fabricated by stubs."""

    route_id: str
    status: Literal["completed"]
    distance_km: float | None
    estimated_duration_min: float | None
    risk_level: Literal["unknown", "low", "moderate", "high"]
    geometry: GeoJSONLineString
    elevation_profile: list[ElevationProfilePoint]
    warnings: list[WarningInfo]
    data_quality: RouteDataQuality
