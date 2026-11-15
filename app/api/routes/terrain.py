"""Terrain and elevation query endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import ErrorResponse
from app.schemas.terrain import ElevationResponse, TerrainResponse

router = APIRouter(prefix="/mars", tags=["terrain"])


def _not_implemented_error() -> HTTPException:
    """Build a consistent response for pending scientific functionality."""
    return HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "This terrain service has not been implemented.",
        },
    )


@router.get("/elevation", response_model=ElevationResponse, responses={501: {"model": ErrorResponse}})
async def get_elevation(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
) -> ElevationResponse:
    """Define the elevation query contract; no validated data source is configured."""
    del latitude, longitude
    raise _not_implemented_error()


@router.get("/terrain", response_model=TerrainResponse, responses={501: {"model": ErrorResponse}})
async def get_terrain(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
) -> TerrainResponse:
    """Define the terrain query contract; measurements are not yet implemented."""
    del latitude, longitude
    raise _not_implemented_error()
