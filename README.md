# Martian Route Planner Backend

Initial FastAPI backend scaffolding for Mars data metadata, terrain queries, and
terrain-aware route planning. Scientific data access and route calculation are
intentionally not implemented; the API does not fabricate measurements or routes.

## Technology stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, NumPy,
Rasterio, GeoPandas, Shapely, Pytest, and HTTPX.

## Project structure

- `app/api/routes/` — health, Mars data, terrain, and route endpoints
- `app/schemas/` — request and response contracts
- `app/services/` — application service interfaces
- `app/algorithms/` — framework-independent algorithm interfaces
- `app/database/` and `app/models/` — SQLAlchemy setup and model stubs
- `data/` — raw, processed, and visual product locations
- `scripts/` — offline ingestion and preprocessing commands
- `tests/` — API and startup tests

## Local setup

Use Python 3.12. From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set `DATA_FILE_PATH` if a static data file path is needed. The API reads
configuration from static files in memory, so it can also run without a database.
The default reads from static data files bundled with the application.

Start the API:

```bash
uvicorn app.main:app --reload
```

The health endpoint is `http://127.0.0.1:8000/api/health`. OpenAPI documentation
is available at `http://127.0.0.1:8000/docs`.

## Environment configuration

Copy `.env.example` to `.env` and update its development-only data file path
before using Docker Compose. Available settings include `API_PREFIX`, `API_VERSION`,
`DATA_FILE_PATH`, and `VISUAL_DATA_DIR`. Do not commit `.env` or real credentials.

## Docker

From this directory:

```bash
cp .env.example .env
docker compose up --build
```

The Compose stack starts the API. The API container is not
blocked on a successful data file health check. The Docker image installs GDAL's
system utilities and development libraries; Rasterio and GeoPandas are installed
from their Python package dependencies.

## Tests

```bash
python -m pytest
```

Tests use the in-process FastAPI test client and require neither NASA datasets nor
a running database.

## Documentation

See the project [documentation index](docs/README.md) for the
[project overview](../docs/PROJECT_OVERVIEW.md), [architecture](../docs/ARCHITECTURE.md),
[API contracts](../docs/API_CONTRACTS.md), and [development plan](../docs/DEVELOPMENT_PLAN.md).
