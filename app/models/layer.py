"""Data model for a validated data-layer record."""

from typing import Optional


class Layer:
    """Metadata record for a data layer; no Mars SRID is assumed."""

    def __init__(
        self,
        id: str,
        name: str,
        available: bool = False,
    ) -> None:
        self.id = id
        self.name = name
        self.available = available


def create_layer(id: str, name: str, available: bool = False) -> Layer:
    """Create a layer instance."""
    return Layer(id=id, name=name, available=available)
