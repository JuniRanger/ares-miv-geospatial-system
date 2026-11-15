"""Health endpoint."""

from pathlib import Path

from fastapi import APIRouter, Response

from app.config import settings
from app.schemas.common import HealthResponse
from app.storage.slope_raster import is_valid_slope_raster

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def get_health(response: Response) -> HealthResponse:
    """Report data availability without requiring datasets or a database."""
    data_dir = Path(__file__).resolve().parents[3] / "data"
    datasets = {
        "slope_raster": (
            "available"
            if is_valid_slope_raster(settings.ruta_pendiente)
            else "unavailable"
        ),
        "science_stops": (
            "available"
            if (data_dir / "science_stops.geojson").is_file()
            else "unavailable"
        ),
        "curiosity_traverse": (
            "available"
            if (data_dir / "raw" / "curiosity_traverse.geojson").is_file()
            else "unavailable"
        ),
    }
    layers = {
        "elevation_m": "unavailable",
        "slope_deg": "unavailable",
        "roughness_m": "unavailable",
        "radiation_mgy_day": "unavailable",
        "thermal_inertia": "unavailable",
    }
    status = "ok" if datasets["slope_raster"] == "available" else "degraded"
    if status == "degraded":
        response.status_code = 503
    return HealthResponse(
        status=status,
        api_version=settings.api_version,
        datasets=datasets,
        layers=layers,
        database_status="disabled",
    )
