
"""Environment-based application configuration."""

from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_LOCAL_DIR = BACKEND_DIR / "data" / "processed"

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

RUTA_PENDIENTE = DEFAULT_DATA_LOCAL_DIR / "slope_5m.tif"


class Settings(BaseSettings):
    """Settings loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    # API
    api_prefix: str = "/api/v1"
    api_version: str = "1.1.0"
    cors_origins: str = "http://localhost:5173"

    # Local data
    data_local_dir: Path = DEFAULT_DATA_LOCAL_DIR
    ruta_pendiente: Path | None = None
    data_file_path: Path = BACKEND_DIR / "data" / "static" / "layers.json"
    visual_data_dir: Path = BACKEND_DIR / "data" / "visual"

    # AWS credentials
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_default_region: str = "us-east-2"

    # S3 configuration
    s3_bucket: str = ""
    s3_key: str = ""
    s3_region: str = "us-east-2"
    s3_endpoint_url: str | None = None

    # Optional dataset integrity
    s3_version_id: str | None = None
    s3_sha256: str | None = None

    @model_validator(mode="after")
    def derive_slope_path(self) -> "Settings":
        """Default the slope raster path to the configured local data directory."""
        if self.ruta_pendiente is None:
            self.ruta_pendiente = self.data_local_dir / "slope_5m.tif"
        return self


settings = Settings()
