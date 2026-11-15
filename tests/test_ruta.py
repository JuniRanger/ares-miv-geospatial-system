"""Pruebas de rutas peatonales con GeoTIFFs sintéticos de 5 m."""

from math import degrees, radians

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from pydantic import ValidationError
from rasterio.transform import from_origin

from app.config import settings
from app.main import app
from app.schemas.route import PeticionRuta

client = TestClient(app)
MARS_RADIUS_M = 3_396_190.0
CELL_SIZE_M = 5.0
CENTER_LON = 137.4
CENTER_LAT = -4.8
MARS_EQC = (
    "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 "
    "+a=3396190 +b=3396190 +units=m +no_defs"
)


def _write_slope_raster(
    path,
    width: int,
    height: int,
    values: np.ndarray | None = None,
) -> tuple[float, float, int, int]:
    center_x = MARS_RADIUS_M * radians(CENTER_LON)
    center_y = MARS_RADIUS_M * radians(CENTER_LAT)
    center_col = width // 2
    center_row = height // 2
    transform = from_origin(
        center_x - (center_col + 0.5) * CELL_SIZE_M,
        center_y + (center_row + 0.5) * CELL_SIZE_M,
        CELL_SIZE_M,
        CELL_SIZE_M,
    )
    slope = values
    if slope is None:
        slope = np.zeros((height, width), dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="float32",
        crs=MARS_EQC,
        transform=transform,
        nodata=-9999.0,
    ) as dataset:
        dataset.write(slope.astype(np.float32), 1)
    return center_x, center_y, center_col, center_row


def _coordinate_at_distance(distance_m: float, axis: str) -> dict[str, float]:
    if axis == "north":
        return {
            "latitude": CENTER_LAT + degrees(distance_m / MARS_RADIUS_M),
            "longitude": CENTER_LON,
        }
    return {
        "latitude": CENTER_LAT,
        "longitude": CENTER_LON + degrees(distance_m / MARS_RADIUS_M),
    }


def _install_raster(tmp_path, monkeypatch, width: int, height: int, values=None):
    path = tmp_path / "slope_test.tif"
    center_x, center_y, center_col, center_row = _write_slope_raster(
        path, width, height, values
    )
    monkeypatch.setenv("RUTA_PENDIENTE", str(path))
    monkeypatch.setattr(settings, "ruta_pendiente", path)
    return path, center_x, center_y, center_col, center_row


def _post_route(origin, destination, **parameters):
    body = {"origin": origin, "destination": destination, **parameters}
    return client.post("/api/v1/routes/plan", json=body)


def test_route_endpoints_publish_request_and_error_contracts():
    paths = app.openapi()["paths"]
    plan_operation = paths["/api/v1/routes/plan"]["post"]
    get_operation = paths["/api/v1/routes/{route_id}"]["get"]

    assert plan_operation["summary"] == "Planificar ruta peatonal marciana"
    assert {"422", "503", "504"} <= set(plan_operation["responses"])
    assert "404" in get_operation["responses"]
    assert "route_id" in get_operation["parameters"][0]["name"]


def test_route_request_has_walker_defaults_and_rejects_rest_distance():
    request = PeticionRuta(
        origin={"latitude": CENTER_LAT, "longitude": CENTER_LON},
        destination=_coordinate_at_distance(500.0, "north"),
    )
    assert request.max_km == 5.0
    assert request.descanso_min == 10.0
    assert request.velocidad_ms == 0.7
    assert request.pendiente_max_deg == 12.0

    with pytest.raises(ValidationError):
        PeticionRuta(
            origin={"latitude": CENTER_LAT, "longitude": CENTER_LON},
            destination=_coordinate_at_distance(500.0, "north"),
            descanso_km=1.0,
        )


def test_flat_three_km_route_has_walker_time_and_rest_segments(tmp_path, monkeypatch):
    _install_raster(tmp_path, monkeypatch, width=60, height=1600)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(3000.0, "north"),
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["distancia_km"] == pytest.approx(3.0, abs=0.01)
    assert 0.9 <= result["tiempo_caminando_h"] <= 1.3
    assert sum(segment["parada"] is not None for segment in result["tramos"]) == 2
    assert result["tramos"][-1]["parada"] is None
    stops = [segment["parada"] for segment in result["tramos"] if segment["parada"]]
    previous_distance = 0.0
    for stop in stops:
        stop_distance = stop["km_acumulado"]
        assert 1.0 <= stop_distance - previous_distance <= 1.5
        previous_distance = stop_distance
    assert "persona caminando con traje espacial, no rover" in result["supuestos"][0]


def test_short_route_has_one_segment_and_no_rest(tmp_path, monkeypatch):
    _install_raster(tmp_path, monkeypatch, width=60, height=400)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(800.0, "north"),
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["tramos"]) == 1
    assert result["tramos"][0]["parada"] is None


def test_astar_crosses_sixty_degree_wall_at_opening(tmp_path, monkeypatch):
    width, height = 600, 100
    slope = np.zeros((height, width), dtype=np.float32)
    wall_col = width // 2
    opening_row = height // 2 - 20
    slope[:, wall_col] = 60.0
    slope[opening_row, wall_col] = 0.0
    _, center_x, center_y, center_col, center_row = _install_raster(
        tmp_path, monkeypatch, width, height, slope
    )
    origin = _coordinate_at_distance(-1250.0, "east")
    destination = _coordinate_at_distance(1250.0, "east")
    response = _post_route(origin, destination)

    assert response.status_code == 200, response.text
    result = response.json()
    opening_lon = CENTER_LON + degrees(
        ((wall_col - center_col) * CELL_SIZE_M) / MARS_RADIUS_M
    )
    opening_lat = CENTER_LAT + degrees(
        ((center_row - opening_row) * CELL_SIZE_M) / MARS_RADIUS_M
    )
    assert any(
        abs(lon - opening_lon) < degrees(CELL_SIZE_M / MARS_RADIUS_M)
        and abs(lat - opening_lat) < degrees(CELL_SIZE_M / MARS_RADIUS_M)
        for lon, lat in result["puntos"]
    )
    assert result["pendiente_max_en_ruta_deg"] == 0.0


def test_start_without_slope_data_returns_422(tmp_path, monkeypatch):
    slope = np.zeros((400, 60), dtype=np.float32)
    slope[200, 30] = -9999.0
    _install_raster(tmp_path, monkeypatch, width=60, height=400, values=slope)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(500.0, "north"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "POINT_NOT_TRAVERSABLE"


def test_start_over_slope_limit_reports_measured_slope(tmp_path, monkeypatch):
    slope = np.zeros((400, 60), dtype=np.float32)
    slope[200, 30] = 12.27
    _install_raster(tmp_path, monkeypatch, width=60, height=400, values=slope)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(500.0, "north"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "POINT_NOT_TRAVERSABLE"
    assert response.json()["details"] == {"slope_deg": 12.27, "max_slope_deg": 12.0}


def test_invalid_raster_returns_service_unavailable(tmp_path, monkeypatch):
    path, *_ = _install_raster(tmp_path, monkeypatch, width=60, height=400)
    path.write_bytes(b"not a GeoTIFF")
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(500.0, "north"),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "INVALID_DATASET"


@pytest.mark.parametrize(
    "parameters",
    [
        {"max_km": 11},
        {"velocidad_ms": 1.5},
        {"pendiente_max_deg": 25},
    ],
)
def test_route_parameter_limits_return_422(parameters):
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(500.0, "north"),
        **parameters,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_direct_distance_over_max_km_returns_422(tmp_path, monkeypatch):
    _install_raster(tmp_path, monkeypatch, width=60, height=2400)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(5100.0, "north"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DIRECT_DISTANCE_EXCEEDED"


def test_point_outside_raster_returns_422(tmp_path, monkeypatch):
    _install_raster(tmp_path, monkeypatch, width=60, height=400)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(1500.0, "north"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "POINT_OUTSIDE_MAP"


def test_no_opening_in_wall_returns_422(tmp_path, monkeypatch):
    width, height = 100, 80
    slope = np.zeros((height, width), dtype=np.float32)
    slope[:, width // 2] = 60.0
    _install_raster(tmp_path, monkeypatch, width, height, slope)
    response = _post_route(
        _coordinate_at_distance(-100.0, "east"),
        _coordinate_at_distance(100.0, "east"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "NO_FEASIBLE_ROUTE"


def test_route_over_max_km_returns_422(tmp_path, monkeypatch):
    width, height = 900, 260
    slope = np.zeros((height, width), dtype=np.float32)
    wall_col = width // 2
    opening_row = height // 2 - 120
    slope[:, wall_col] = 60.0
    slope[opening_row, wall_col] = 0.0
    _install_raster(tmp_path, monkeypatch, width, height, slope)
    response = _post_route(
        _coordinate_at_distance(-2000.0, "east"),
        _coordinate_at_distance(2000.0, "east"),
        max_km=4.1,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "ROUTE_DISTANCE_EXCEEDED"


def test_search_expansion_limit_returns_504(tmp_path, monkeypatch):
    from app.algorithms import astar

    _install_raster(tmp_path, monkeypatch, width=60, height=1600)
    monkeypatch.setattr(astar, "MAX_EXPANSIONES", 1)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(1000.0, "north"),
    )

    assert response.status_code == 504
    assert response.json()["code"] == "SEARCH_LIMIT_EXCEEDED"