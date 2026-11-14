"""Interface for retrieving validated geological vector data."""

from app.schemas.mars import GeoJSONFeatureCollection


def get_geology_features(layer_id: str) -> GeoJSONFeatureCollection:
    """Return GeoJSON features for a validated geology layer."""
    raise NotImplementedError("Geological data access is not implemented.")
