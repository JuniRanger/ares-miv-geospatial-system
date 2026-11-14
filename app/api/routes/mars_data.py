"""Endpoints for Mars layer metadata and visual products."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path as PathParameter
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas.common import LayerListResponse, LayerMetadata

router = APIRouter(prefix="/mars", tags=["Mars data"])

_PLANNED_LAYERS = (
    ("elevation", "Elevation", "Planned elevation layer."),
    ("slope", "Slope", "Planned slope layer."),
    ("roughness", "Roughness", "Planned terrain roughness layer."),
    ("thermal", "Thermal", "Planned thermal layer."),
    ("geology", "Geology", "Planned geology layer."),
)


def _unavailable_dataset_error(resource: str) -> HTTPException:
    """Build a consistent response for a product that is not available."""
    return HTTPException(
        status_code=404,
        detail={
            "code": "DATASET_UNAVAILABLE",
            "message": f"The requested {resource} is not available.",
        },
    )


@router.get("/layers", response_model=LayerListResponse)
async def list_layers() -> LayerListResponse:
    """List planned data categories without claiming datasets are available."""
    layers = [
        LayerMetadata(
            layer_id=layer_id,
            name=name,
            description=f"{description} No dataset has been validated for this layer.",
            available=False,
            source=None,
            units=None,
            spatial_resolution=None,
            coordinate_reference_system=None,
        )
        for layer_id, name, description in _PLANNED_LAYERS
    ]
    return LayerListResponse(layers=layers)


@router.get("/texture")
async def get_texture() -> FileResponse:
    """Serve the generated global texture when it exists."""
    texture_path = settings.visual_data_dir / "mars_texture.png"
    if not texture_path.is_file():
        raise _unavailable_dataset_error("Mars texture")
    return FileResponse(texture_path, media_type="image/png")


@router.get("/layers/{layer_id}/raster")
async def get_layer_raster(
    layer_id: Annotated[str, PathParameter(min_length=1)],
) -> FileResponse:
    """Serve a generated PNG visualization for a layer when it exists."""
    if Path(layer_id).name != layer_id or layer_id in {".", ".."}:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested raster visualization was not found.",
            },
        )

    raster_path = settings.visual_data_dir / f"{layer_id}.png"
    if not raster_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested raster visualization was not found.",
            },
        )
    return FileResponse(raster_path, media_type="image/png")


@router.get("/layers/{layer_id}/data")
async def get_layer_data(
    layer_id: Annotated[str, PathParameter(min_length=1)],
) -> None:
    """Report vector data as unavailable until a validated product exists."""
    raise HTTPException(
        status_code=503,
        detail={
            "code": "DATASET_UNAVAILABLE",
            "message": f"Vector data for layer '{layer_id}' is not available.",
        },
    )
