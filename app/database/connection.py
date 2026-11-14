"""In-memory storage for static data files."""

from collections.abc import Generator
from typing import Any, Dict, List, Optional

from app.config import settings


class DataStore:
    """Simple in-memory store for static data files loaded at startup."""

    def __init__(self) -> None:
        self._layers: Dict[str, Any] = {}
        self._routes: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Load static data from the configured file path."""
        if self._initialized:
            return
        try:
            import json
            file_path = settings.data_file_path
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for item in data:
                            if isinstance(item, dict):
                                layer_id = item.get("id") or item.get("layer_id")
                                if layer_id:
                                    self._layers[str(layer_id)] = item
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                layer_id = item.get("id") or item.get("layer_id")
                                if layer_id:
                                    self._layers[str(layer_id)] = item
            self._initialized = True
        except Exception:
            # If static file is missing or invalid, start with empty store
            self._initialized = True

    def get_layer(self, layer_id: str) -> Optional[Any]:
        """Get a layer by ID from the in-memory store."""
        return self._layers.get(str(layer_id))

    def get_layers(self) -> List[Any]:
        """Get all layers from the in-memory store."""
        return list(self._layers.values())

    def save_route(self, route: Any) -> str:
        """Save a route and return its ID."""
        import uuid
        route_id = str(uuid.uuid4())
        self._routes[route_id] = route
        return route_id

    def get_route(self, route_id: str) -> Optional[Any]:
        """Get a route by ID from the in-memory store."""
        return self._routes.get(route_id)

    def get_routes(self) -> List[Any]:
        """Get all routes from the in-memory store."""
        return list(self._routes.values())


store = DataStore()
