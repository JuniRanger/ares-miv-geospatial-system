"""Route planning request and response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import (
    DESCANSO_MIN_DEFECTO,
    KM_DEFECTO,
    KM_MAX,
    PEND_MAX_DEFECTO,
    PEND_TOPE,
    VEL_DEFECTO_MS,
    VEL_MAX_MS,
)
from app.schemas.coordinates import Coordinates


class PeticionRuta(BaseModel):
    """Request for a suited human route over the slope raster."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "origin": {
                    "latitude": -4.814930942114384,
                    "longitude": 137.37203786800262,
                },
                "destination": {
                    "latitude": -4.822185302203374,
                    "longitude": 137.363433859525,
                },
                "max_km": 5.0,
                "descanso_min": 10,
                "velocidad_ms": 0.7,
                "pendiente_max_deg": 12,
            }
        },
    )

    origin: Coordinates = Field(description="Inicio de la ruta en latitud/longitud marciana.")
    destination: Coordinates = Field(description="Destino de la ruta en latitud/longitud marciana.")
    descanso_min: float = Field(
        default=DESCANSO_MIN_DEFECTO,
        gt=0,
        description="Duración en minutos de cada parada sugerida.",
    )
    velocidad_ms: float = Field(
        default=VEL_DEFECTO_MS,
        gt=0,
        le=VEL_MAX_MS,
        description="Velocidad nominal de caminata en m/s; máximo del modelo 1.0 m/s.",
    )
    pendiente_max_deg: float = Field(
        default=PEND_MAX_DEFECTO,
        gt=0,
        le=PEND_TOPE,
        description="Pendiente máxima transitable en grados; celdas superiores son impasables.",
    )
    max_km: float = Field(
        default=KM_DEFECTO,
        gt=0,
        le=KM_MAX,
        description="Límite de distancia directa y de longitud total de ruta en km.",
    )


RoutePlanRequest = PeticionRuta


class Parada(BaseModel):
    """Suggested rest stop located on the calculated route."""

    lon: float = Field(description="Longitud este de la parada en grados.")
    lat: float = Field(description="Latitud planetocéntrica de la parada en grados.")
    km_acumulado: float = Field(description="Distancia desde el inicio hasta la parada en km.")


class Tramo(BaseModel):
    """Walking segment between the start or two consecutive rest stops."""

    tramo: int = Field(description="Índice del tramo, empezando en 1.")
    km: float = Field(description="Distancia de este tramo en km.")
    horas_caminando: float = Field(description="Tiempo caminando de este tramo, sin descanso, en horas.")
    parada: Parada | None = Field(description="Parada al final del tramo; null para el tramo final.")


class RouteResponse(BaseModel):
    """JSON response with route geometry, stages, timings and assumptions."""

    distancia_km: float = Field(description="Longitud total de la ruta calculada en km.")
    resolucion_m: float = Field(description="Resolución lineal del GeoTIFF en metros por celda.")
    pendiente_max_en_ruta_deg: float = Field(description="Máxima pendiente encontrada en la ruta, en grados.")
    puntos: list[tuple[float, float]] = Field(description="Píxeles de la ruta como pares [longitud, latitud].")
    tramos: list[Tramo] = Field(description="Tramos caminables separados por paradas sugeridas.")
    tiempo_caminando_h: float = Field(description="Tiempo total de caminata, sin descansos, en horas.")
    tiempo_descanso_h: float = Field(description="Tiempo total de descanso en horas.")
    tiempo_total_h: float = Field(description="Suma de caminata y descansos en horas.")
    supuestos: list[str] = Field(description="Supuestos científicos y de movimiento del modelo.")
