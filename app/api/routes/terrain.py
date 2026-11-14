"""Terrain and elevation query endpoints."""

from fastapi import APIRouter, HTTPException, Query

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


@router.get("/elevation", response_model=ElevationResponse)
async def get_elevation(
    latitude: float = Query(...),
    longitude: float = Query(...),
) -> ElevationResponse:
    """Define the elevation query contract; no validated data source is configured."""
    del latitude, longitude
    raise _not_implemented_error()


@router.get("/terrain", response_model=TerrainResponse)
async def get_terrain(
    latitude: float = Query(...),
    longitude: float = Query(...),
) -> TerrainResponse:
    """Define the terrain query contract; measurements are not yet implemented."""
    del latitude, longitude
    raise _not_implemented_error()
