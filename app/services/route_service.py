"""Planificación de rutas peatonales sobre el raster de pendiente."""

from dataclasses import dataclass
from math import ceil, cos, degrees, hypot, radians
from pathlib import Path

import numpy as np
import rasterio
from numpy.typing import NDArray

from app.algorithms.astar import ExpansionLimitExceeded, find_path
from app.config import (
    PEND_REF,
    PEND_TOPE,
    RUTA_PENDIENTE,
    TRAMO_MAX_KM,
    TRAMO_MIN_KM,
    settings,
)
from app.schemas.route import Parada, PeticionRuta, RouteResponse, Tramo


@dataclass
class RoutePlanningError(Exception):
    """Error de dominio que el endpoint traduce a una respuesta HTTP."""

    status_code: int
    code: str
    message: str
    details: dict[str, object] | None = None


def plan_route(request: PeticionRuta) -> RouteResponse:
    """Calcular una ruta humana y sus descansos a partir de un GeoTIFF."""
    raster_path = Path(settings.ruta_pendiente or RUTA_PENDIENTE)
    if not raster_path.is_file():
        raise RoutePlanningError(
            503,
            "DATASET_UNAVAILABLE",
            f"No se encontró el raster de pendiente configurado: {raster_path}",
        )

    with rasterio.open(raster_path) as dataset:
        if dataset.crs is None:
            raise RoutePlanningError(
                503, "INVALID_DATASET", "El raster de pendiente no declara un CRS."
            )
        projection = dataset.crs.to_dict()
        if projection.get("proj") != "eqc":
            raise RoutePlanningError(
                503,
                "INVALID_DATASET",
                "El raster debe usar una proyección equirectangular esférica.",
            )

        radius_m = float(projection.get("R", projection.get("a", 0.0)))
        if radius_m <= 0:
            raise RoutePlanningError(
                503,
                "INVALID_DATASET",
                "El CRS del raster no declara el radio de la esfera de Marte.",
            )
        origin_xy = _lonlat_to_xy(request.origin.longitude, request.origin.latitude, projection, radius_m)
        destination_xy = _lonlat_to_xy(
            request.destination.longitude,
            request.destination.latitude,
            projection,
            radius_m,
        )
        origin_cell = dataset.index(*origin_xy)
        destination_cell = dataset.index(*destination_xy)
        _ensure_in_bounds(origin_cell, dataset.height, dataset.width, "inicio")
        _ensure_in_bounds(destination_cell, dataset.height, dataset.width, "destino")
        direct_distance_m = hypot(
            destination_xy[0] - origin_xy[0], destination_xy[1] - origin_xy[1]
        )
        max_distance_m = request.max_km * 1000.0
        if direct_distance_m > max_distance_m:
            raise RoutePlanningError(
                422,
                "DIRECT_DISTANCE_EXCEEDED",
                "La distancia directa supera max_km.",
                {"direct_distance_km": direct_distance_m / 1000.0},
            )

        pixel_width_m = abs(float(dataset.transform.a))
        pixel_height_m = abs(float(dataset.transform.e))
        search_window = _search_window(
            dataset.width,
            dataset.height,
            origin_cell,
            max_distance_m,
            pixel_width_m,
            pixel_height_m,
        )
        slope = dataset.read(1, window=search_window, masked=True)
        slope_values = np.asarray(slope.data, dtype=np.float32)
        valid = ~np.ma.getmaskarray(slope) & np.isfinite(slope_values)
        valid &= slope_values >= 0.0
        valid &= slope_values <= request.pendiente_max_deg

        origin_local = (
            origin_cell[0] - int(search_window.row_off),
            origin_cell[1] - int(search_window.col_off),
        )
        destination_local = (
            destination_cell[0] - int(search_window.row_off),
            destination_cell[1] - int(search_window.col_off),
        )
        _ensure_cell_traversable(
            slope_values, valid, origin_local, "inicio", request.pendiente_max_deg
        )
        _ensure_cell_traversable(
            slope_values, valid, destination_local, "destino", request.pendiente_max_deg
        )

        cost_grid = _build_cost_grid(slope_values, valid)
        try:
            local_path = find_path(
                cost_grid,
                origin_local,
                destination_local,
                pixel_width_m,
                pixel_height_m,
            )
        except ExpansionLimitExceeded as error:
            raise RoutePlanningError(
                504,
                "SEARCH_LIMIT_EXCEEDED",
                "La búsqueda superó el límite de expansiones permitido.",
            ) from error

        if local_path is None:
            raise RoutePlanningError(
                422, "NO_FEASIBLE_ROUTE", "No existe una ruta transitable entre los puntos."
            )

        global_path = [
            (
                row + int(search_window.row_off),
                col + int(search_window.col_off),
            )
            for row, col in local_path
        ]
        route_slopes = np.asarray(
            [slope_values[row - int(search_window.row_off), col - int(search_window.col_off)]
             for row, col in global_path],
            dtype=np.float64,
        )
        cumulative_m = _cumulative_distances(
            global_path, pixel_width_m, pixel_height_m
        )
        distance_m = cumulative_m[-1]
        if distance_m > max_distance_m + 1e-6:
            raise RoutePlanningError(
                422,
                "ROUTE_DISTANCE_EXCEEDED",
                "La longitud de la ruta calculada supera max_km.",
                {"route_distance_km": distance_m / 1000.0},
            )

        points = [
            _xy_to_lonlat(*dataset.xy(row, col), projection, radius_m)
            for row, col in global_path
        ]
        stop_indices = _select_rest_stops(cumulative_m, route_slopes)
        segments = _build_segments(
            stop_indices,
            cumulative_m,
            route_slopes,
            points,
            request.velocidad_ms,
        )

    walking_hours = sum(segment.horas_caminando for segment in segments)
    resting_hours = len(stop_indices) * request.descanso_min / 60.0
    return RouteResponse(
        distancia_km=distance_m / 1000.0,
        resolucion_m=(pixel_width_m + pixel_height_m) / 2.0,
        pendiente_max_en_ruta_deg=float(np.max(route_slopes)),
        puntos=points,
        tramos=segments,
        tiempo_caminando_h=walking_hours,
        tiempo_descanso_h=resting_hours,
        tiempo_total_h=walking_hours + resting_hours,
        supuestos=_model_assumptions(),
    )


def _lonlat_to_xy(
    longitude: float,
    latitude: float,
    projection: dict[str, object],
    radius_m: float,
) -> tuple[float, float]:
    """Convertir lon/lat a metros usando los parámetros Eqc del GeoTIFF."""
    central_lon = float(projection.get("lon_0", 0.0))
    central_lat = float(projection.get("lat_0", 0.0))
    standard_lat = radians(float(projection.get("lat_ts", 0.0)))
    x_m = float(projection.get("x_0", 0.0)) + radius_m * cos(standard_lat) * radians(
        longitude - central_lon
    )
    y_m = float(projection.get("y_0", 0.0)) + radius_m * radians(latitude - central_lat)
    return x_m, y_m


def _xy_to_lonlat(
    x_m: float,
    y_m: float,
    projection: dict[str, object],
    radius_m: float,
) -> tuple[float, float]:
    """Convertir metros de la proyección Eqc a lon/lat."""
    central_lon = float(projection.get("lon_0", 0.0))
    central_lat = float(projection.get("lat_0", 0.0))
    standard_lat = radians(float(projection.get("lat_ts", 0.0)))
    false_easting = float(projection.get("x_0", 0.0))
    false_northing = float(projection.get("y_0", 0.0))
    longitude = central_lon + degrees(
        (x_m - false_easting) / (radius_m * cos(standard_lat))
    )
    latitude = central_lat + degrees((y_m - false_northing) / radius_m)
    return longitude, latitude


def _ensure_in_bounds(
    cell: tuple[int, int], height: int, width: int, label: str
) -> None:
    if not (0 <= cell[0] < height and 0 <= cell[1] < width):
        raise RoutePlanningError(
            422, "POINT_OUTSIDE_MAP", f"El punto de {label} está fuera del mapa."
        )


def _ensure_cell_traversable(
    slope_values: NDArray[np.float32],
    valid: NDArray[np.bool_],
    cell: tuple[int, int],
    label: str,
    max_slope_deg: float,
) -> None:
    if valid[cell]:
        return

    observed_slope = float(round(float(slope_values[cell]), 4))
    if np.isfinite(observed_slope) and observed_slope > max_slope_deg:
        raise RoutePlanningError(
            422,
            "POINT_NOT_TRAVERSABLE",
            f"El punto de {label} tiene una pendiente de {observed_slope:.2f}°, "
            f"superior al límite de {max_slope_deg:.2f}°.",
            {"slope_deg": observed_slope, "max_slope_deg": max_slope_deg},
        )

    raise RoutePlanningError(
        422,
        "POINT_NOT_TRAVERSABLE",
        f"El punto de {label} está en una zona sin dato o inválida.",
    )


def _search_window(
    width: int,
    height: int,
    origin: tuple[int, int],
    max_distance_m: float,
    pixel_width_m: float,
    pixel_height_m: float,
) -> rasterio.windows.Window:
    """Limitar la lectura al radio máximo que puede recorrer el usuario."""
    col_radius = ceil(max_distance_m / pixel_width_m) + 1
    row_radius = ceil(max_distance_m / pixel_height_m) + 1
    col_start = max(0, origin[1] - col_radius)
    row_start = max(0, origin[0] - row_radius)
    col_stop = min(width, origin[1] + col_radius + 1)
    row_stop = min(height, origin[0] + row_radius + 1)
    return rasterio.windows.Window(
        col_start, row_start, col_stop - col_start, row_stop - row_start
    )


def _build_cost_grid(
    slope_values: NDArray[np.float32], valid: NDArray[np.bool_]
) -> NDArray[np.float64]:
    """Crear costos crecientes desde PEND_REF y bloquear datos inválidos."""
    cost_grid = np.full(slope_values.shape, np.inf, dtype=np.float64)
    valid_slopes = slope_values[valid].astype(np.float64)
    cost_grid[valid] = 1.0 + np.square(valid_slopes / PEND_REF)
    return cost_grid


def _cumulative_distances(
    path: list[tuple[int, int]], pixel_width_m: float, pixel_height_m: float
) -> list[float]:
    distances = [0.0]
    for previous, current in zip(path, path[1:]):
        row_delta = (current[0] - previous[0]) * pixel_height_m
        col_delta = (current[1] - previous[1]) * pixel_width_m
        distances.append(distances[-1] + hypot(row_delta, col_delta))
    return distances


def _select_rest_stops(
    cumulative_m: list[float], slopes: NDArray[np.float64]
) -> list[int]:
    """Seleccionar el mínimo local entre 1 y 1,5 km, nunca en el destino."""
    stop_indices: list[int] = []
    previous_stop_m = 0.0
    previous_index = 0
    max_segment_m = TRAMO_MAX_KM * 1000.0
    min_segment_m = TRAMO_MIN_KM * 1000.0

    while cumulative_m[-1] - previous_stop_m >= max_segment_m:
        lower_bound = previous_stop_m + min_segment_m
        upper_bound = previous_stop_m + max_segment_m
        candidates = [
            index
            for index in range(previous_index + 1, len(cumulative_m) - 1)
            if lower_bound <= cumulative_m[index] <= upper_bound
        ]
        if not candidates:
            break
        stop_index = min(
            candidates,
            key=lambda index: (
                float(slopes[index]),
                abs(cumulative_m[index] - lower_bound),
            ),
        )
        stop_indices.append(stop_index)
        previous_index = stop_index
        previous_stop_m = cumulative_m[stop_index]
    return stop_indices


def _build_segments(
    stop_indices: list[int],
    cumulative_m: list[float],
    slopes: NDArray[np.float64],
    points: list[tuple[float, float]],
    speed_ms: float,
) -> list[Tramo]:
    boundaries = [0, *stop_indices, len(cumulative_m) - 1]
    segments: list[Tramo] = []
    stop_set = set(stop_indices)
    for segment_number, (start_index, end_index) in enumerate(
        zip(boundaries, boundaries[1:]), start=1
    ):
        walking_seconds = 0.0
        for index in range(start_index + 1, end_index + 1):
            step_distance = cumulative_m[index] - cumulative_m[index - 1]
            local_slope = max(0.0, float((slopes[index - 1] + slopes[index]) / 2.0))
            actual_speed = speed_ms * max(0.2, 1.0 - local_slope / PEND_TOPE)
            walking_seconds += step_distance / actual_speed

        stop: Parada | None = None
        if end_index in stop_set:
            longitude, latitude = points[end_index]
            stop = Parada(
                lon=longitude,
                lat=latitude,
                km_acumulado=cumulative_m[end_index] / 1000.0,
            )
        segments.append(
            Tramo(
                tramo=segment_number,
                km=(cumulative_m[end_index] - cumulative_m[start_index]) / 1000.0,
                horas_caminando=walking_seconds / 3600.0,
                parada=stop,
            )
        )
    return segments


def _model_assumptions() -> list[str]:
    return [
        "Modelo: persona caminando con traje espacial, no rover.",
        "La velocidad máxima nominal se basa en Apolo: 3,5 km/h medidos en la Luna.",
        "La velocidad por defecto, la duración del descanso y la reducción por pendiente son supuestos del modelo.",
        "La pendiente máxima se extrapola de pruebas de la NASA con traje (~11°) y no está validada.",
        "La pendiente proviene del DEM a 5 m; no es la inclinación real bajo el traje.",
        "No hay mediciones de caminata con traje presurizado en gravedad marciana.",
    ]


def get_route(route_id: str) -> RouteResponse:
    """La persistencia de rutas no forma parte de este flujo de cálculo."""
    raise RoutePlanningError(404, "RESOURCE_NOT_FOUND", f"No existe la ruta {route_id}.")
