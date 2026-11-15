"""Tests for pending and unavailable API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unimplemented_terrain_endpoints_return_501() -> None:
    """Terrain endpoints disclose that scientific lookup is pending."""
    elevation = client.get(
        "/api/mars/elevation", params={"latitude": -4.5, "longitude": 137.4}
    )
    terrain = client.get(
        "/api/mars/terrain", params={"latitude": -4.5, "longitude": 137.4}
    )

    assert elevation.status_code == 501
    assert elevation.json()["error"]["code"] == "NOT_IMPLEMENTED"
    assert terrain.status_code == 501
    assert terrain.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_route_planning_returns_501_without_fake_route() -> None:
    """The route endpoint never returns a fabricated successful route."""
    response = client.post(
        "/api/routes/plan",
        json={
            "origin": {"latitude": -4.5, "longitude": 137.4},
            "destination": {"latitude": -4.6, "longitude": 137.5},
            "preferences": {},
        },
    )

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_missing_visual_products_return_consistent_404() -> None:
    """Missing image products return errors rather than placeholder files."""
    for path in (
        "/api/mars/texture",
        "/api/mars/layers/elevation/raster",
    ):
        response = client.get(path)

        assert response.status_code == 404
        assert response.json()["error"]["code"] in {
            "DATASET_UNAVAILABLE",
            "RESOURCE_NOT_FOUND",
        }


def test_vector_data_is_unavailable_without_a_validated_dataset() -> None:
    """The vector endpoint does not invent an empty FeatureCollection."""
    response = client.get("/api/mars/layers/geology/data")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATASET_UNAVAILABLE"


def test_unknown_route_returns_404() -> None:
    """Route retrieval reports missing persisted routes honestly."""
    response = client.get("/api/routes/not-a-saved-route")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
