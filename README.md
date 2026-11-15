# Martian Route Planner Backend

FastAPI backend for Mars data metadata, terrain queries, and human walking-route
planning. The route endpoint runs A* over a local slope GeoTIFF; other scientific
data services remain pending and the API does not fabricate measurements.

## Technology stack

Python 3.12, FastAPI, Pydantic v2, boto3, SQLAlchemy 2.x, NumPy,
Rasterio, GeoPandas, Shapely, Docker Compose, Pytest, and HTTPX.

## Project structure

- `app/api/routes/` — health, Mars data, terrain, and route endpoints
- `app/schemas/` — request and response contracts
- `app/services/` — route planning and data services
- `app/algorithms/` — framework-independent A* and terrain algorithms
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

Copy `.env.example` to `.env` and set `RUTA_PENDIENTE` to the 5 m slope GeoTIFF
cache path (default: `./data/processed/slope_5m.tif`). Configure the S3 bucket
and key to allow the API to populate this cache in the background. The API can
start without AWS credentials or an available raster; route planning returns
503 until a valid local raster is present.

To fetch or refresh the raster manually:

```bash
python scripts/fetch_route_raster.py
python scripts/fetch_route_raster.py --force
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The health endpoint is `http://127.0.0.1:8000/api/v1/health`, route planning is
`POST http://127.0.0.1:8000/api/v1/routes/plan`, and OpenAPI documentation is at
`http://127.0.0.1:8000/docs`.

## Environment configuration

Docker Compose starts with defaults; copy `.env.example` to `.env` only when
overriding them. Available settings include `API_PREFIX`, `API_VERSION`,
`CORS_ORIGINS`, `DATA_LOCAL_DIR`, `RUTA_PENDIENTE`, `DATA_FILE_PATH`, and
`VISUAL_DATA_DIR`, plus `S3_BUCKET`, `S3_KEY`, `S3_REGION`, optional
`S3_VERSION_ID` and `S3_SHA256`, and optional AWS credentials. Without explicit
keys, boto3 uses its standard credential chain. `RUTA_PENDIENTE` selects the
5 m slope GeoTIFF; it is validated during startup and opened for each route.
`CORS_ORIGINS` is a comma-separated list and defaults to
`http://localhost:5173`. Do not commit `.env` or credentials.

## Docker

From this directory:

```bash
docker compose up --build
```

The Compose stack starts the API with a writable raster-cache directory; no
database container is required. Missing datasets make `/api/v1/health` return
`503` with `status: "degraded"`, but do not prevent the application from
starting. Rasterio and GeoPandas are installed from their Python dependencies.

## Tests

```bash
python -m pytest
```

Tests use the in-process FastAPI test client and require neither NASA datasets nor
a running database.

## Documentation

See the [route planning guide](docs/ROUTE_PLANNING.md), [API contracts](docs/API_CONTRACTS.md),
[project overview](docs/PROJECT_OVERVIEW.md), [architecture](docs/ARCHITECTURE.md),
[raw data ingestion guide](docs/RAW_DATA_INGESTION.md), and [development plan](docs/DEVELOPMENT_PLAN.md).
