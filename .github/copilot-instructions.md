
# GitHub Copilot Instructions

## 1. Project Context

This repository contains the backend for **Martian Route Planner**, a project developed for NASA Space Apps Challenge 2026.

The goal is to provide a backend capable of analyzing Martian terrain data and planning routes between two geographic coordinates.

The backend is responsible for:
- Providing terrain and elevation information.
- Managing available scientific datasets.
- Processing geospatial information.
- Calculating terrain-aware routes using A*.
- Returning route geometry, elevation profiles, and risk warnings.
- Exposing all functionality through a REST API.

The frontend is responsible for the 3D Mars globe, visualization, camera controls, and user interaction.

The backend must NOT implement frontend visualization.

## 2. Development Constraints

This project is being developed during a 24-hour hackathon.

Prioritize:
- Working functionality over unnecessary abstraction.
- A demonstrable end-to-end workflow.
- Simple architecture.
- Minimal dependencies.
- Clear API contracts.
- Reliable integration with the frontend.

Do not introduce unnecessary complexity.

Avoid microservices, Kafka, Redis, Celery, Kubernetes, or complex infrastructure unless explicitly requested.

## 3. Technology Stack

Use the following technologies:

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- PostgreSQL
- PostGIS
- NumPy
- Rasterio
- GDAL
- GeoPandas
- Shapely
- Pytest
- HTTPX
- Docker
- Docker Compose

Do not introduce additional dependencies without a clear technical reason.

## 4. Architecture

Use a modular monolith architecture.

Respect the following responsibilities:

### API
Location: `app/api/routes/`

- Define HTTP endpoints.
- Validate incoming requests through Pydantic schemas.
- Call application services.
- Return consistent HTTP responses.
- Do not implement business logic or geospatial calculations.

### Schemas
Location: `app/schemas/`

- Define request and response models.
- Use Pydantic v2.
- Validate input types and constraints.
- Keep API contracts consistent.

### Services
Location: `app/services/`

- Implement application and domain logic.
- Coordinate data access and algorithms.
- Handle dataset availability.
- Avoid placing HTTP-specific logic here.

### Algorithms
Location: `app/algorithms/`

- Implement A* pathfinding.
- Implement terrain cost calculations.
- Implement risk analysis.
- Keep algorithms independent of FastAPI and database concerns.

### Database
Location: `app/database/`

- Manage database configuration and sessions.
- Implement repositories and data access.
- Use SQLAlchemy 2.x.
- Prepare PostGIS integration without assuming an unverified Mars SRID.

### Models
Location: `app/models/`

- Define SQLAlchemy models.
- Keep persistence models separate from API schemas.

### Scripts
Location: `scripts/`

- Handle dataset ingestion and preprocessing.
- Keep expensive raster processing outside normal API requests.

## 5. Scientific Data Integrity

This is a critical project requirement.

NEVER:
- Invent scientific measurements.
- Invent NASA datasets or data sources.
- Invent spatial resolutions.
- Invent coordinate reference systems.
- Invent dataset coverage.
- Present illustrative values as real measurements.
- Claim a layer is available when it has not been downloaded and validated.

When data is unavailable:
- Return null for unavailable measurements.
- Include explicit data availability information.
- Return appropriate warnings.
- Do not fabricate fallback values.

Preserve the original dataset's metadata, units, and coordinate reference information.

## 6. Mars Geospatial Conventions

Do not automatically assume that terrestrial geospatial conventions apply to Mars.

Before implementing geospatial calculations, verify:

- Planetocentric or planetographic latitude.
- Longitude direction.
- Coordinate reference system.
- Datum or reference surface.
- Spatial resolution.
- Units.
- Dataset coverage.

API coordinate objects should use named fields:

{
  "latitude": -4.5,
  "longitude": 137.4
}

GeoJSON coordinates must follow the standard order:

[longitude, latitude]

Never calculate physical distances by treating longitude and latitude degrees as linear distances.

Keep coordinate conversion logic centralized and documented.

## 7. API Development Rules

- Use REST conventions.
- Use explicit Pydantic request and response models.
- Use appropriate HTTP status codes.
- Keep endpoints small and readable.
- Do not expose internal database models directly.
- Do not return large raw raster arrays inside JSON.
- Use GeoJSON for geographic geometries.
- Use PNG or appropriate image formats for visual raster products.
- Use metadata to communicate available layers and their properties.

Unimplemented functionality must return an honest response, such as HTTP 501.

Do not simulate successful route calculations with fabricated data.

## 8. Data Processing Rules

NASA datasets should be downloaded and processed separately from normal API requests.

Expected workflow:

1. Obtain source datasets.
2. Inspect their metadata.
3. Validate coordinate systems and units.
4. Preprocess and align datasets when necessary.
5. Generate analytical products.
6. Store processed products.
7. Expose them through API services.

Separate:
- Analytical products used by algorithms.
- Visual products consumed by the frontend.

Do not process entire planetary datasets on every API request.

## 9. Coding Standards

- Use Python type hints.
- Prefer clear and descriptive names.
- Use small, focused functions.
- Add docstrings to public classes and functions.
- Avoid duplicated logic.
- Handle exceptions explicitly.
- Keep configuration in environment variables.
- Never hardcode credentials.
- Follow PEP 8.
- Avoid unnecessary abstractions.

Use async endpoints where appropriate, but do not force asynchronous execution for CPU-intensive geospatial processing.

## 10. Testing

- Use Pytest.
- Test API endpoints with HTTPX.
- Test services independently.
- Test algorithms with small deterministic inputs.
- Mock unavailable external datasets and services.
- Ensure the application can start without scientific datasets.
- Do not require real NASA downloads for basic tests.

## 11. Documentation

Before implementing a feature, consult the relevant documentation inside `docs/`.

Important documents:

- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACTS.md`
- `docs/DEVELOPMENT_PLAN.md`

If an architectural decision is missing, do not invent it silently.

Ask for clarification when necessary or document the assumption explicitly.

When changing API contracts, architecture, data formats, or scientific assumptions, update the corresponding documentation.

## 12. Implementation Behavior

Before modifying files:

1. Inspect the existing repository.
2. Understand the current structure.
3. Read relevant documentation.
4. Identify existing implementations.
5. Avoid overwriting working code unnecessarily.

When implementing a feature:

1. Make the smallest complete implementation.
2. Respect module responsibilities.
3. Add validation and error handling.
4. Add or update tests.
5. Verify imports and application startup.
6. Report what was implemented and what remains incomplete.

Never claim that a feature is implemented if it is only a stub or placeholder.

## 13. Priority

The main objective is to deliver a functional backend within the hackathon timeframe.

Prioritize in this order:

1. Backend structure and application startup.
2. API contracts and health endpoint.
3. Real Mars elevation dataset integration.
4. Terrain data access.
5. A* route planning.
6. GeoJSON route responses.
7. Additional terrain layers.
8. Risk analysis and refinements.

Do not let optional features delay the core route-planning workflow.
