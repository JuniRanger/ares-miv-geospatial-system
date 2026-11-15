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
