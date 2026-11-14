"""Shared API response schemas."""

from typing import Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Machine-readable error information."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Consistent API error envelope."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """API availability information."""

    status: Literal["ok"]
    api_version: str
    storage_status: Literal["not_checked"] = "not_checked"


class WarningInfo(BaseModel):
    """A warning associated with a measurement or route."""

    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class DataAvailability(BaseModel):
    """Availability of measurements at a requested location."""

    elevation: bool
    slope: bool
    roughness: bool
    thermal: bool


class LayerMetadata(BaseModel):
    """Public metadata for a data layer; unknown source properties stay null."""

    layer_id: str
    name: str
    description: str
    available: bool
    source: str | None
    units: str | None
    spatial_resolution: str | None
    coordinate_reference_system: str | None


class LayerListResponse(BaseModel):
    """Collection of known layer metadata."""

    layers: list[LayerMetadata]
