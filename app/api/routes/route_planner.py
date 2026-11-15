"""Route planning and retrieval endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.route import RoutePlanRequest, RouteResponse

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RoutePlanRequest) -> RouteResponse:
    """Accept the route contract without returning a fabricated route."""
    del request
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Route planning has not been implemented.",
        },
    )


# @router.get("/{route_id}", response_model=RouteResponse)
# async def get_route(route_id: str) -> RouteResponse:
#     """Return 404 because no route persistence or route records exist yet."""
#     del route_id
#     raise HTTPException(
#         status_code=404,
#         detail={
#             "code": "RESOURCE_NOT_FOUND",
#             "message": "The requested route was not found.",
#         },
#     )
