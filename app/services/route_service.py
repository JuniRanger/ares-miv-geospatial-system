"""Interface for terrain-aware route planning and retrieval."""

from app.schemas.route import RoutePlanRequest, RouteResponse


def plan_route(request: RoutePlanRequest) -> RouteResponse:
    """Calculate and persist a route using validated terrain products."""
    raise NotImplementedError("Route planning is not implemented.")


def get_route(route_id: str) -> RouteResponse:
    """Retrieve a previously calculated route by identifier."""
    raise NotImplementedError("Route retrieval is not implemented.")
