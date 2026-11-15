"""Environment-based application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]

KM_MAX = 10.0
KM_DEFECTO = 5.0
TRAMO_MIN_KM = 1.0
TRAMO_MAX_KM = 1.5
VEL_MAX_MS = 1.0
VEL_DEFECTO_MS = 0.7
DESCANSO_MIN_DEFECTO = 10.0
PEND_MAX_DEFECTO = 12.0
PEND_TOPE = 20.0
PEND_REF = 10.0
MAX_EXPANSIONES = 500_000
RUTA_PENDIENTE = BACKEND_DIR / "map_mart" / "slope_5m.tif"


class Settings(BaseSettings):
    """Settings loaded from environment variables and an optional .env file."""

    api_prefix: str = "/api/v1"
    api_version: str = "1.1.0"
    cors_origins: str = "http://localhost:5173"
    data_local_dir: Path = BACKEND_DIR / "data" / "processed"
    ruta_pendiente: Path = RUTA_PENDIENTE
    data_file_path: Path = BACKEND_DIR / "data" / "static" / "layers.json"
    visual_data_dir: Path = BACKEND_DIR / "data" / "visual"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
