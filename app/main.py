"""FastAPI application factory and API router registration."""

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import health, mars_data, route_planner, stubs, terrain
from app.config import settings
from app.schemas.common import ErrorDetail, ErrorResponse
from app.storage.s3_downloader import ensure_slope_raster
from app.storage.slope_raster import is_valid_slope_raster

logger = logging.getLogger(__name__)


async def _prepare_slope_dataset(application: FastAPI) -> None:
    """Refresh the local raster cache outside the event loop."""
    try:
        result = await asyncio.to_thread(ensure_slope_raster)
        application.state.slope_dataset_available = result.available
        if not result.available:
            logger.warning(
                "El raster de pendiente no está disponible (%s).",
                result.error_code or result.status,
            )
    except Exception as error:
        application.state.slope_dataset_available = False
        logger.error(
            "Falló la preparación del raster durante el inicio (%s).",
            type(error).__name__,
        )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Start the API immediately and refresh the dataset asynchronously."""
    application.state.slope_dataset_available = is_valid_slope_raster(
        settings.ruta_pendiente
    )
    refresh_task = asyncio.create_task(_prepare_slope_dataset(application))
    try:
        yield
    finally:
        await refresh_task


def create_app() -> FastAPI:
    """Create the API application without requiring external services or datasets."""
    application = FastAPI(
        title="Martian Route Planner API",
        description=(
            "Backend API for Mars data metadata, terrain queries, and human route planning. "
            "Route planning requires a validated local slope GeoTIFF."
        ),
        version=settings.api_version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix=settings.api_prefix)
    application.include_router(mars_data.router, prefix=settings.api_prefix)
    application.include_router(terrain.router, prefix=settings.api_prefix)
    application.include_router(route_planner.router, prefix=settings.api_prefix)
    application.include_router(stubs.router, prefix=settings.api_prefix)

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exception: StarletteHTTPException
    ) -> JSONResponse:
        """Return HTTP errors in the API's consistent error format."""
        if isinstance(exception.detail, dict):
            detail = ErrorDetail.model_validate(exception.detail)
        else:
            detail = ErrorDetail(code="HTTP_ERROR", message=str(exception.detail))
        return JSONResponse(
            status_code=exception.status_code,
            content=ErrorResponse(**detail.model_dump()).model_dump(exclude_none=True),
            headers=exception.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        """Return request validation failures in the API's error format."""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="The request does not match the required API contract.",
            details={"issues": jsonable_encoder(exception.errors())},
        )
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(**detail.model_dump()).model_dump(exclude_none=True),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exception: Exception
    ) -> JSONResponse:
        """Log unexpected failures and return a non-sensitive error response."""
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        detail = ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(**detail.model_dump()).model_dump(exclude_none=True),
        )

    return application


app = create_app()
