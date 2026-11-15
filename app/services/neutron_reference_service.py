"""Referencia regional de neutrones Odyssey para las zonas de una ruta."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from app.schemas.route import ReferenciaNeutrones, ZonaNeutrones

AND_PRODUCT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "and_13_225_240.dat"
)
AND_RECORD_DTYPE = np.dtype(
    [
        ("latitude_deg", ">f4"),
        ("longitude_east_deg", ">f4"),
        ("thermal_counts_s", ">f4"),
        ("thermal_intervals", ">f4"),
        ("thermal_std_counts_s", ">f4"),
        ("epithermal_counts_s", ">f4"),
        ("epithermal_intervals", ">f4"),
        ("epithermal_std_counts_s", ">f4"),
        ("fast_counts_s", ">f4"),
        ("fast_intervals", ">f4"),
        ("fast_std_counts_s", ">f4"),
    ]
)
_EXPECTED_RECORDS = 36 * 72
_GRID_STEP_DEG = 5.0
_PRODUCT_METADATA = {
    "fuente": "Mars Odyssey GRS / Neutron Spectrometer, producto AND",
    "producto_id": "ODY-M-GRS-5-AND-V2.0 / AND_13_225_240",
    "fecha_inicio_utc": "2026-02-13T00:00:00Z",
    "fecha_fin_utc": "2026-03-09T00:00:00Z",
    "longitud_solar_inicio_deg": 225.0,
    "longitud_solar_fin_deg": 240.0,
    "resolucion_espacial_deg": (5.0, 5.0),
    "unidad": "cuentas/s",
}


def get_route_neutron_reference(
    route_points: list[tuple[float, float]],
) -> ReferenciaNeutrones:
    """Obtener tasas AND para cada celda de 5° atravesada por la ruta."""
    if not route_points:
        return _unavailable_reference("La ruta no contiene puntos para consultar.")

    try:
        records = np.fromfile(AND_PRODUCT_PATH, dtype=AND_RECORD_DTYPE)
    except OSError:
        return _unavailable_reference("No se encontró el producto AND local.")

    if records.size != _EXPECTED_RECORDS:
        return _unavailable_reference(
            "El producto AND no contiene las 2592 celdas esperadas."
        )

    records_by_zone = {
        (
            round(float(record["latitude_deg"]), 1),
            round(float(record["longitude_east_deg"]), 1),
        ): record
        for record in records
    }
    zone_keys = list(dict.fromkeys(_zone_key(latitude, longitude) for longitude, latitude in route_points))
    zones = [
        _build_zone(zone_key, records_by_zone)
        for zone_key in zone_keys
    ]
    available_zones = sum(
        zone.termicos_cuentas_s is not None
        and zone.epitermicos_cuentas_s is not None
        for zone in zones
    )
    status = (
        "available"
        if available_zones == len(zones)
        else "partial" if available_zones else "unavailable"
    )
    return ReferenciaNeutrones(
        estado=status,
        **_PRODUCT_METADATA,
        mensaje=(
            "Conteos regionales de neutrones; no son dosis de radiación ni se usan "
            "como costo de A*. La resolución es mucho más gruesa que la ruta de 5 m."
        ),
        zonas=zones,
    )


def _zone_key(latitude_deg: float, longitude_deg: float) -> tuple[float, float]:
    """Asignar latitud/longitud a la celda de 5° que contiene el punto."""
    latitude_index = min(
        35,
        max(0, int(np.floor((90.0 - latitude_deg) / _GRID_STEP_DEG))),
    )
    longitude_east_deg = longitude_deg % 360.0
    longitude_index = int(np.floor(longitude_east_deg / _GRID_STEP_DEG)) % 72
    latitude_center = 87.5 - latitude_index * _GRID_STEP_DEG
    longitude_center = 2.5 + longitude_index * _GRID_STEP_DEG
    return round(latitude_center, 1), round(longitude_center, 1)


def _build_zone(
    zone_key: tuple[float, float],
    records_by_zone: dict[tuple[float, float], np.void],
) -> ZonaNeutrones:
    record = records_by_zone.get(zone_key)
    if record is None:
        return ZonaNeutrones(
            latitud_centro_areocentrica_deg=zone_key[0],
            longitud_centro_este_deg=zone_key[1],
            celdas_vecinas_disponibles=0,
            termicos_cuentas_s=None,
            termicos_desviacion_cuentas_s=None,
            termicos_intervalos=None,
            termicos_media_vecinos_cuentas_s=None,
            termicos_diferencia_vecinos_pct=None,
            epitermicos_cuentas_s=None,
            epitermicos_desviacion_cuentas_s=None,
            epitermicos_intervalos=None,
            epitermicos_media_vecinos_cuentas_s=None,
            epitermicos_diferencia_vecinos_pct=None,
        )

    neighbors = [
        neighbor
        for latitude_offset in (-_GRID_STEP_DEG, 0.0, _GRID_STEP_DEG)
        for longitude_offset in (-_GRID_STEP_DEG, 0.0, _GRID_STEP_DEG)
        if latitude_offset != 0.0 or longitude_offset != 0.0
        if (
            neighbor := records_by_zone.get(
                (
                    round(zone_key[0] + latitude_offset, 1),
                    round((zone_key[1] + longitude_offset) % 360.0, 1),
                )
            )
        ) is not None
    ]

    thermal_rate = _finite_nonnegative(record["thermal_counts_s"])
    epithermal_rate = _finite_nonnegative(record["epithermal_counts_s"])
    thermal_neighbor_mean = _neighbor_mean(neighbors, "thermal_counts_s")
    epithermal_neighbor_mean = _neighbor_mean(neighbors, "epithermal_counts_s")
    return ZonaNeutrones(
        latitud_centro_areocentrica_deg=zone_key[0],
        longitud_centro_este_deg=zone_key[1],
        celdas_vecinas_disponibles=len(neighbors),
        termicos_cuentas_s=thermal_rate,
        termicos_desviacion_cuentas_s=_finite_nonnegative(
            record["thermal_std_counts_s"]
        ),
        termicos_intervalos=_valid_interval_count(record["thermal_intervals"]),
        termicos_media_vecinos_cuentas_s=thermal_neighbor_mean,
        termicos_diferencia_vecinos_pct=_relative_difference(
            thermal_rate, thermal_neighbor_mean
        ),
        epitermicos_cuentas_s=epithermal_rate,
        epitermicos_desviacion_cuentas_s=_finite_nonnegative(
            record["epithermal_std_counts_s"]
        ),
        epitermicos_intervalos=_valid_interval_count(
            record["epithermal_intervals"]
        ),
        epitermicos_media_vecinos_cuentas_s=epithermal_neighbor_mean,
        epitermicos_diferencia_vecinos_pct=_relative_difference(
            epithermal_rate, epithermal_neighbor_mean
        ),
    )


def _neighbor_mean(
    neighbors: list[np.void], field_name: str
) -> float | None:
    values = [
        value
        for neighbor in neighbors
        if (value := _finite_nonnegative(neighbor[field_name])) is not None
    ]
    return float(np.mean(values)) if values else None


def _relative_difference(value: float | None, reference: float | None) -> float | None:
    if value is None or reference is None or reference <= 0.0:
        return None
    return (value - reference) / reference * 100.0


def _finite_nonnegative(value: np.generic | float) -> float | None:
    converted = float(value)
    return converted if np.isfinite(converted) and converted >= 0.0 else None


def _valid_interval_count(value: np.generic | float) -> int | None:
    converted = _finite_nonnegative(value)
    return int(converted) if converted is not None else None


def _unavailable_reference(message: str) -> ReferenciaNeutrones:
    return ReferenciaNeutrones(
        estado="unavailable",
        **_PRODUCT_METADATA,
        mensaje=message,
        zonas=[],
    )