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
from app.services import neutron_reference_service

client = TestClient(app)
MARS_RADIUS_M = 3_396_190.0
CELL_SIZE_M = 5.0
CENTER_LON = 137.4
CENTER_LAT = -4.8
MARS_EQC = (
    "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 "
    "+a=3396190 +b=3396190 +units=m +no_defs"
)
AND_TEST_DTYPE = neutron_reference_service.AND_RECORD_DTYPE


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


def _write_and_product(path):
    records = np.zeros(36 * 72, dtype=AND_TEST_DTYPE)
    for latitude_index in range(36):
        for longitude_index in range(72):
            record_index = latitude_index * 72 + longitude_index
            records[record_index]["latitude_deg"] = 87.5 - latitude_index * 5
            records[record_index]["longitude_east_deg"] = 2.5 + longitude_index * 5
            records[record_index]["thermal_counts_s"] = 2.0
            records[record_index]["thermal_intervals"] = 40
            records[record_index]["thermal_std_counts_s"] = 0.2
            records[record_index]["epithermal_counts_s"] = 3.0
            records[record_index]["epithermal_intervals"] = 40
            records[record_index]["epithermal_std_counts_s"] = 0.3
            records[record_index]["fast_counts_s"] = 1.0
            records[record_index]["fast_intervals"] = 40
            records[record_index]["fast_std_counts_s"] = 0.1

    gale_index = 18 * 72 + 27
    records[gale_index]["thermal_counts_s"] = 2.5
    records[gale_index]["epithermal_counts_s"] = 3.5
    records.tofile(path)


def test_route_endpoints_publish_request_and_error_contracts():
    paths = app.openapi()["paths"]
    plan_operation = paths["/api/v1/routes/plan"]["post"]
    get_operation = paths["/api/v1/routes/{route_id}"]["get"]
    response_ref = plan_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    response_model = response_ref.rsplit("/", 1)[-1]
    response_fields = app.openapi()["components"]["schemas"][response_model]["properties"]

    assert plan_operation["summary"] == "Planificar ruta peatonal marciana"
    assert {"422", "503", "504"} <= set(plan_operation["responses"])
    assert "referencia_neutrones" in response_fields
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


def test_route_includes_regional_neutron_reference(tmp_path, monkeypatch):
    _install_raster(tmp_path, monkeypatch, width=60, height=400)
    and_path = tmp_path / "and_test.dat"
    _write_and_product(and_path)
    monkeypatch.setattr(neutron_reference_service, "AND_PRODUCT_PATH", and_path)
    response = _post_route(
        {"latitude": CENTER_LAT, "longitude": CENTER_LON},
        _coordinate_at_distance(800.0, "north"),
    )

    assert response.status_code == 200, response.text
    reference = response.json()["referencia_neutrones"]
    assert reference["estado"] == "available"
    assert reference["producto_id"] == "ODY-M-GRS-5-AND-V2.0 / AND_13_225_240"
    assert reference["fecha_inicio_utc"] == "2026-02-13T00:00:00Z"
    assert reference["fecha_fin_utc"] == "2026-03-09T00:00:00Z"
    assert reference["resolucion_espacial_deg"] == [5.0, 5.0]
    assert reference["es_dosis"] is False
    assert reference["usada_por_astar"] is False
    assert len(reference["zonas"]) == 1
    zone = reference["zonas"][0]
    assert zone["latitud_centro_areocentrica_deg"] == -2.5
    assert zone["longitud_centro_este_deg"] == 137.5
    assert zone["termicos_cuentas_s"] == 2.5
    assert zone["termicos_media_vecinos_cuentas_s"] == 2.0
    assert zone["termicos_diferencia_vecinos_pct"] == pytest.approx(25.0)
    assert zone["epitermicos_cuentas_s"] == 3.5
    assert zone["epitermicos_media_vecinos_cuentas_s"] == 3.0
    assert zone["epitermicos_diferencia_vecinos_pct"] == pytest.approx(100 / 6)


def test_neutron_reference_includes_each_5_degree_zone_crossed(tmp_path, monkeypatch):
    and_path = tmp_path / "and_test.dat"
    _write_and_product(and_path)
    monkeypatch.setattr(neutron_reference_service, "AND_PRODUCT_PATH", and_path)

    reference = neutron_reference_service.get_route_neutron_reference(
        [(4.9, 0.0), (5.1, 0.0)]
    )

    assert reference.estado == "available"
    assert len(reference.zonas) == 2
    assert [zone.longitud_centro_este_deg for zone in reference.zonas] == [2.5, 7.5]
    assert all(zone.latitud_centro_areocentrica_deg == -2.5 for zone in reference.zonas)


def test_neutron_reference_is_unavailable_without_and_product(tmp_path, monkeypatch):
    monkeypatch.setattr(
        neutron_reference_service, "AND_PRODUCT_PATH", tmp_path / "missing-and.dat"
    )

    reference = neutron_reference_service.get_route_neutron_reference(
        [(CENTER_LON, CENTER_LAT)]
    )

    assert reference.estado == "unavailable"
    assert reference.zonas == []
    assert reference.mensaje == "No se encontró el producto AND local."
    assert reference.es_dosis is False


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