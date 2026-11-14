"""Data model for a calculated route."""

from typing import Optional


class Route:
    """Route record placeholder without unverified geometry or spatial metadata."""

    def __init__(
        self,
        id: str,
        status: str,
    ) -> None:
        self.id = id
        self.status = status


def create_route(id: str, status: str = "pending") -> Route:
    """Create a route instance."""
    return Route(id=id, status=status)
