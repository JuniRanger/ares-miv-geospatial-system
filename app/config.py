"""Environment-based application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Settings loaded from environment variables and an optional .env file."""

    api_prefix: str = "/api"
    api_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://localhost/martian_route_planner"
    visual_data_dir: Path = BACKEND_DIR / "data" / "visual"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
