"""Health endpoint."""

from fastapi import APIRouter, Response

from app.config import settings
from app.schemas.common import HealthResponse
from pathlib import Path

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def get_health(response: Response) -> HealthResponse:
    """Report data availability without requiring datasets or a database."""
    data_dir = Path(__file__).resolve().parents[3] / "data"
    dataset_paths = {
        "cost_stack": settings.data_local_dir / "cost_stack.tif",
        "science_stops": data_dir / "science_stops.geojson",
        "curiosity_traverse": data_dir / "raw" / "curiosity_traverse.geojson",
    }
    datasets = {
        name: "available" if path.is_file() else "unavailable"
        for name, path in dataset_paths.items()
    }
    layers = {
        "elevation_m": "unavailable",
        "slope_deg": "unavailable",
        "roughness_m": "unavailable",
        "radiation_mgy_day": "unavailable",
        "thermal_inertia": "unavailable",
    }
    status = "ok" if datasets["cost_stack"] == "available" else "degraded"
    if status == "degraded":
        response.status_code = 503
    return HealthResponse(
        status=status,
        api_version=settings.api_version,
        datasets=datasets,
        layers=layers,
        database_status="disabled",
    )
