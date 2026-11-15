"""Shared API response schemas."""

from typing import Any, Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Machine-readable error information."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Consistent API error envelope."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """API availability information."""

    status: Literal["ok", "degraded"]
    api_version: str
    datasets: dict[str, Literal["available", "unavailable"]]
    layers: dict[str, Literal["available", "partial", "estimated", "unavailable"]]
    database_status: Literal["disabled"] = "disabled"


class WarningInfo(BaseModel):
    """A warning associated with a measurement or route."""

    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"
    latitude: float
    longitude: float
    distance_m: float
    length_m: float | None = None


class DataAvailability(BaseModel):
    """Availability of measurements at a requested location."""

    elevation: bool
    slope: bool
    roughness: bool
    thermal: bool
    radiation: bool = False


class LayerMetadata(BaseModel):
    """Public metadata for a data layer; unknown source properties stay null."""

    layer_id: str
    name: str
    description: str
    category: Literal[
        "optical", "topographic", "thermal", "spectral", "geologic", "radiation", "derived"
    ] = "derived"
    role: Literal["display", "cost"] = "display"
    quality: Literal["available", "partial", "estimated", "unavailable"] = "unavailable"
    available: bool
    source: str | None
    units: str | None
    spatial_resolution: str | None
    coordinate_reference_system: str | None
    tile_url: str | None = None
    raster_url: str | None = None
    tiling_scheme: dict[str, Any] | None = None
    bbox: tuple[float, float, float, float] | None = None
    max_level: int | None = None
    default_opacity: float | None = None
    legend: dict[str, Any] | None = None


class LayerListResponse(BaseModel):
    """Collection of known layer metadata."""

    layers: list[LayerMetadata]
