"""Tests for pending and unavailable API endpoints."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_unimplemented_terrain_endpoints_return_501() -> None:
    """Terrain endpoints disclose that scientific lookup is pending."""
    elevation = client.get(
        "/api/v1/mars/elevation", params={"latitude": -4.5, "longitude": 137.4}
    )
    terrain = client.get(
        "/api/v1/mars/terrain", params={"latitude": -4.5, "longitude": 137.4}
    )

    assert elevation.status_code == 501
    assert elevation.json()["code"] == "NOT_IMPLEMENTED"
    assert terrain.status_code == 501
    assert terrain.json()["code"] == "NOT_IMPLEMENTED"


def test_route_planning_reports_missing_raster_without_fake_route(
    tmp_path, monkeypatch
) -> None:
    """The route endpoint does not claim success when no slope raster exists."""
    monkeypatch.setattr(settings, "ruta_pendiente", tmp_path / "missing-slope.tif")
    response = client.post(
        "/api/v1/routes/plan",
        json={
            "origin": {"latitude": -4.5, "longitude": 137.4},
            "destination": {"latitude": -4.6, "longitude": 137.5},
        },
    )

    assert response.status_code == 503
    assert response.json()["code"] == "DATASET_UNAVAILABLE"


def test_missing_visual_products_return_consistent_404() -> None:
    """Missing image products return errors rather than placeholder files."""
    for path in (
        "/api/v1/mars/texture",
        "/api/v1/mars/layers/elevation/raster",
    ):
        response = client.get(path)

        assert response.status_code == 404
        assert response.json()["code"] in {
            "DATASET_UNAVAILABLE",
            "RESOURCE_NOT_FOUND",
        }


def test_vector_data_is_unavailable_without_a_validated_dataset() -> None:
    """The vector endpoint does not invent an empty FeatureCollection."""
    response = client.get("/api/v1/mars/layers/geology/data")

    assert response.status_code == 503
    assert response.json()["code"] == "DATASET_UNAVAILABLE"


def test_unknown_route_returns_404() -> None:
    """Route retrieval reports missing persisted routes honestly."""
    response = client.get("/api/v1/routes/not-a-saved-route")

    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"


def test_required_scaffold_stubs_return_501() -> None:
    """Planned endpoints are registered and fail honestly until implemented."""
    for path in (
        "/api/v1/site",
        "/api/v1/mars/traverse/curiosity",
        "/api/v1/mars/images/near?latitude=-4.5&longitude=137.4",
    ):
        response = client.get(path)

        assert response.status_code == 501
        assert response.json()["code"] == "NOT_IMPLEMENTED"


def test_invalid_route_request_uses_validation_error_contract() -> None:
    """Invalid requests use the documented 422 error code without tracebacks."""
    response = client.post("/api/v1/routes/plan", json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "Traceback" not in response.text


def test_cors_preflight_allows_frontend_origin() -> None:
    """The configured frontend origin can make browser API requests."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_does_not_allow_unconfigured_origin() -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_route_rejects_latitude_outside_mars_coordinate_range() -> None:
    response = client.post(
        "/api/v1/routes/plan",
        json={
            "origin": {"latitude": 91, "longitude": 137.4},
            "destination": {"latitude": -4.6, "longitude": 137.5},
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
