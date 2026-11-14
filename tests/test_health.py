"""Health endpoint and startup tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_api_status_without_database_check() -> None:
    """Health remains available without requiring a storage connection."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "0.1.0",
        "storage_status": "not_checked",
    }


def test_all_api_routers_are_registered() -> None:
    """The application exposes the expected API route families."""
    paths = {route.path for route in app.routes}

    assert {
        "/api/health",
        "/api/mars/layers",
        "/api/mars/texture",
        "/api/mars/elevation",
        "/api/mars/terrain",
        "/api/mars/layers/{layer_id}/raster",
        "/api/mars/layers/{layer_id}/data",
        "/api/routes/plan",
        "/api/routes/{route_id}",
    } <= paths


def test_missing_datasets_do_not_prevent_startup() -> None:
    """Layer metadata and the app remain available when no data is configured."""
    response = client.get("/api/mars/layers")

    assert response.status_code == 200
    assert response.json()["layers"]
    assert all(not layer["available"] for layer in response.json()["layers"])
