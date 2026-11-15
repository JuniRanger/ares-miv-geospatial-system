"""Schemas describing Mars data metadata and GeoJSON features."""

from typing import Any, Literal

from pydantic import BaseModel


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry coordinates use the standard [longitude, latitude] order."""

    type: Literal["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"]
    coordinates: list[Any]


class GeoJSONFeature(BaseModel):
    """GeoJSON feature without assumptions about scientific properties."""

    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONGeometry | None
    properties: dict[str, Any] | None


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON feature collection."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]


class SiteGrid(BaseModel):
    """Master grid metadata for the configured study area."""

    resolution_m: float
    width_cells: int
    height_cells: int
    coordinate_reference_system: str


class SiteDEM(BaseModel):
    """Provenance and range metadata for the site's elevation product."""

    source: str
    source_resolution_m: float
    elevation_min_m: float | None
    elevation_max_m: float | None


class SiteResponse(BaseModel):
    """Study-area response defined by the API contract."""

    site_id: str
    name: str
    bbox: tuple[float, float, float, float]
    grid: SiteGrid
    dem: SiteDEM
    science_stops: GeoJSONFeatureCollection
