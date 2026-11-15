"""Shared validation for the local single-band slope GeoTIFF."""

from dataclasses import asdict, dataclass
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import DatasetReader


class SlopeRasterValidationError(ValueError):
    """Raised when a raster does not meet the route planner's input contract."""


@dataclass(frozen=True)
class SlopeRasterMetadata:
    """Small, JSON-safe set of slope raster properties for the cache manifest."""

    width: int
    height: int
    band_count: int
    dtype: str
    crs: str
    mars_radius_m: float
    resolution_x_m: float
    resolution_y_m: float
    band_unit: str | None
    nodata: int | float | str | None
    bounds: tuple[float, float, float, float]
    transform: tuple[float, float, float, float, float, float]

    def as_dict(self) -> dict[str, object]:
        """Return metadata suitable for JSON serialization."""
        metadata = asdict(self)
        metadata["bounds"] = list(self.bounds)
        metadata["transform"] = list(self.transform)
        return metadata


def validate_slope_dataset(dataset: DatasetReader) -> SlopeRasterMetadata:
    """Validate raster properties consumed by the existing route service."""
    if dataset.count != 1:
        raise SlopeRasterValidationError("El GeoTIFF debe tener exactamente una banda.")
    if dataset.width <= 0 or dataset.height <= 0:
        raise SlopeRasterValidationError("El GeoTIFF debe tener dimensiones positivas.")
    if dataset.crs is None:
        raise SlopeRasterValidationError("El GeoTIFF no declara un CRS.")

    projection = dataset.crs.to_dict()
    if projection.get("proj") != "eqc":
        raise SlopeRasterValidationError(
            "El CRS debe usar una proyección equirectangular esférica."
        )
    mars_radius_m = float(projection.get("R", projection.get("a", 0.0)))
    if not math.isfinite(mars_radius_m) or mars_radius_m <= 0:
        raise SlopeRasterValidationError(
            "El CRS debe declarar un radio planetario positivo."
        )

    linear_units = projection.get("units")
    if linear_units is None:
        linear_units = getattr(dataset.crs, "linear_units", None)
    if str(linear_units).lower() not in {"m", "meter", "meters", "metre", "metres"}:
        raise SlopeRasterValidationError(
            "Las unidades lineales del CRS deben ser metros."
        )

    transform = dataset.transform
    transform_values = tuple(float(value) for value in transform[:6])
    if not all(math.isfinite(value) for value in transform_values):
        raise SlopeRasterValidationError("La geotransformación no es válida.")
    if transform.is_identity or transform.b != 0 or transform.d != 0:
        raise SlopeRasterValidationError(
            "El GeoTIFF debe tener una geotransformación north-up sin rotación."
        )

    resolution_x_m = abs(float(transform.a))
    resolution_y_m = abs(float(transform.e))
    if not math.isclose(resolution_x_m, 5.0, rel_tol=0.0, abs_tol=1e-6) or not math.isclose(
        resolution_y_m, 5.0, rel_tol=0.0, abs_tol=1e-6
    ):
        raise SlopeRasterValidationError(
            "La resolución esperada para slope_5m.tif es de 5 m por píxel."
        )

    dtype = np.dtype(dataset.dtypes[0])
    if dtype.kind not in "uif":
        raise SlopeRasterValidationError(
            "La banda debe usar un tipo numérico real compatible con Rasterio."
        )

    band_unit = dataset.units[0] if dataset.units else None
    if band_unit and band_unit.strip().lower() not in {
        "deg",
        "degree",
        "degrees",
        "degree(s)",
    }:
        raise SlopeRasterValidationError(
            "La banda declara unidades distintas de grados."
        )

    nodata = dataset.nodatavals[0]
    if isinstance(nodata, (float, np.floating)) and not math.isfinite(float(nodata)):
        nodata = "NaN" if math.isnan(float(nodata)) else str(nodata)

    bounds = dataset.bounds
    return SlopeRasterMetadata(
        width=dataset.width,
        height=dataset.height,
        band_count=dataset.count,
        dtype=str(dtype),
        crs=dataset.crs.to_string(),
        mars_radius_m=mars_radius_m,
        resolution_x_m=resolution_x_m,
        resolution_y_m=resolution_y_m,
        band_unit=band_unit,
        nodata=nodata,
        bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
        transform=transform_values,
    )


def inspect_slope_raster(path: Path) -> SlopeRasterMetadata:
    """Open and validate a slope raster without reading its pixel array."""
    try:
        with rasterio.open(path) as dataset:
            return validate_slope_dataset(dataset)
    except SlopeRasterValidationError:
        raise
    except (OSError, rasterio.errors.RasterioError) as error:
        raise SlopeRasterValidationError(
            "No se pudo abrir el GeoTIFF de pendiente."
        ) from error


def is_valid_slope_raster(path: Path) -> bool:
    """Return whether a local path contains a valid slope raster."""
    if not path.is_file():
        return False
    try:
        inspect_slope_raster(path)
    except SlopeRasterValidationError:
        return False
    return True
