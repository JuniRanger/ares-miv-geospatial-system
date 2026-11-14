"""Health endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthResponse
from app.database.connection import store

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Report API health without making a storage connection."""
    store.initialize()
    return HealthResponse(
        status="ok",
        api_version=settings.api_version,
        storage_status="ok" if store._initialized else "not_checked",
    )
