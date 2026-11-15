"""Route planning and retrieval endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.route import PeticionRuta, RouteResponse
from app.services.route_service import RoutePlanningError, get_route as retrieve_route
from app.services.route_service import plan_route as calculate_route

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post(
    "/plan",
    response_model=RouteResponse,
    summary="Planificar ruta peatonal marciana",
    description=(
        "Calcula una ruta para una persona con traje usando el GeoTIFF de pendiente "
        "configurado por RUTA_PENDIENTE. Los errores 422 indican puntos o rutas no "
        "transitables; 503 indica que el raster no está disponible o no es compatible; "
        "504 indica que se superó el límite de expansiones de A*."
    ),
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Solicitud inválida, punto fuera del mapa, zona impasable o ruta fuera del límite.",
        },
        503: {
            "model": ErrorResponse,
            "description": "GeoTIFF ausente, sin CRS o con proyección incompatible.",
        },
        504: {
            "model": ErrorResponse,
            "description": "A* superó el máximo de expansiones permitido.",
        },
    },
)
def plan_route(request: PeticionRuta) -> RouteResponse:
    """Calcular una ruta peatonal sin mantener el GeoTIFF abierto."""
    try:
        return calculate_route(request)
    except RoutePlanningError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={
                "code": error.code,
                "message": error.message,
                "details": error.details,
            },
        ) from error


@router.get(
    "/{route_id}",
    response_model=RouteResponse,
    summary="Consultar ruta calculada",
    description="La persistencia de rutas no está habilitada; actualmente responde 404.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "No existe una ruta persistida con ese identificador.",
        }
    },
)
def get_route(route_id: str) -> RouteResponse:
    """Indicar que no hay persistencia para recuperar rutas por id."""
    try:
        return retrieve_route(route_id)
    except RoutePlanningError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
