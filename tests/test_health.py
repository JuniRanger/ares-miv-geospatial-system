"""Health endpoint and startup tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.storage.s3_downloader import DatasetPreparationResult

client = TestClient(app)


def test_health_reports_missing_datasets_without_database(tmp_path, monkeypatch) -> None:
    """Health reports degraded data status while the API remains startable."""
    from app.config import settings

    monkeypatch.setattr(settings, "ruta_pendiente", tmp_path / "missing-slope.tif")
    response = client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["api_version"] == "1.1.0"
    assert body["database_status"] == "disabled"
    assert set(body["datasets"]) == {
        "slope_raster",
        "science_stops",
        "curiosity_traverse",
    }
    assert set(body["layers"]) == {
        "elevation_m",
        "slope_deg",
        "roughness_m",
        "radiation_mgy_day",
        "thermal_inertia",
    }
    assert set(body["datasets"].values()) == {"unavailable"}
    assert set(body["layers"].values()) == {"unavailable"}


def test_all_api_routers_are_registered() -> None:
    """The application exposes the expected API route families."""
    paths = set(app.openapi()["paths"])

    assert {
        "/api/v1/health",
        "/api/v1/site",
        "/api/v1/mars/layers",
        "/api/v1/mars/terrain",
        "/api/v1/mars/traverse/curiosity",
        "/api/v1/mars/images/near",
        "/api/v1/mars/layers/{layer_id}/raster",
        "/api/v1/routes/plan",
        "/api/v1/routes/{route_id}",
    } <= paths


def test_missing_datasets_do_not_prevent_startup() -> None:
    """Layer metadata and the app remain available when no data is configured."""
    response = client.get("/api/v1/mars/layers")

    assert response.status_code == 200
    assert response.json()["layers"]
    assert all(not layer["available"] for layer in response.json()["layers"])


def test_lifespan_starts_when_slope_raster_is_unavailable(monkeypatch, tmp_path) -> None:
    """A missing cache or remote object does not prevent FastAPI startup."""
    calls = []

    def unavailable_result():
        calls.append(True)
        return DatasetPreparationResult(
            status="unavailable",
            available=False,
            path=tmp_path / "missing.tif",
            message="No raster is available.",
        )

    monkeypatch.setattr("app.main.is_valid_slope_raster", lambda _path: False)
    monkeypatch.setattr("app.main.ensure_slope_raster", unavailable_result)

    with TestClient(app) as startup_client:
        response = startup_client.get("/api/v1/mars/layers")

    assert response.status_code == 200
    assert calls == [True]
