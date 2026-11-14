# Martian Route Planner Backend

Initial FastAPI backend scaffolding for Mars data metadata, terrain queries, and
terrain-aware route planning. Scientific data access and route calculation are
intentionally not implemented; the API does not fabricate measurements or routes.

## Technology stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL/PostGIS, NumPy,
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

Set `DATABASE_URL` if a PostgreSQL connection is needed. The API does not connect
to the database during startup, so it can also run while PostgreSQL is unavailable.
The default URL targets a local PostgreSQL service and does not include credentials.

Start the API:

```bash
uvicorn app.main:app --reload
```

The health endpoint is `http://127.0.0.1:8000/api/health`. OpenAPI documentation
is available at `http://127.0.0.1:8000/docs`.

## Environment configuration

Copy `.env.example` to `.env` and update its development-only PostgreSQL credentials
before using Docker Compose. Available settings include `API_PREFIX`, `API_VERSION`,
`DATABASE_URL`, and `VISUAL_DATA_DIR`. Do not commit `.env` or real credentials.

## Docker

From this directory:

```bash
cp .env.example .env
docker compose up --build
```

The Compose stack starts the API and PostgreSQL/PostGIS. The API container is not
blocked on a successful database health check. The Docker image installs GDAL's
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
