"""Health endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Report API health without making a database connection."""
    return HealthResponse(
        status="ok",
        api_version=settings.api_version,
        database_status="not_checked",
    )
