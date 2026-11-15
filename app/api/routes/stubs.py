"""Registered API endpoints whose functionality is not implemented yet."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import ErrorResponse
from app.schemas.mars import GeoJSONFeatureCollection, SiteResponse

router = APIRouter(tags=["planned endpoints"])


def _not_implemented(message: str) -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={"code": "NOT_IMPLEMENTED", "message": message},
    )


@router.get(
    "/site",
    response_model=SiteResponse,
    responses={501: {"model": ErrorResponse}},
)
async def get_site() -> SiteResponse:
    """Expose the planned study-area endpoint without inventing metadata."""
    raise _not_implemented("The study area is not available yet.")


@router.get(
    "/mars/traverse/curiosity",
    response_model=GeoJSONFeatureCollection,
    responses={501: {"model": ErrorResponse}},
)
async def get_curiosity_traverse() -> GeoJSONFeatureCollection:
    """Expose the planned traverse endpoint without fabricated coordinates."""
    raise _not_implemented("The Curiosity traverse is not available yet.")


@router.get("/mars/images/near", responses={501: {"model": ErrorResponse}})
async def get_images_near(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
) -> None:
    """Expose the planned image lookup without fabricated image results."""
    del latitude, longitude
    raise _not_implemented("Nearby Curiosity images are not available yet.")