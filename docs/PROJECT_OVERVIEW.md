# Project Overview

## Martian Route Planner

Martian Route Planner is a prototype backend for exploring terrain information on Mars and planning a route between an origin and a destination.

The project is being developed for NASA Space Apps Challenge 2026. The development window is limited to 24 hours, so the implementation must prioritize a demonstrable end-to-end workflow over broad feature coverage.

## Backend responsibilities

1. Expose a REST API through FastAPI.
2. Provide metadata describing available Mars data layers.
3. Provide terrain measurements for requested coordinates or regions when datasets exist.
4. Accept route-planning requests.
5. Eventually calculate a route using terrain-aware pathfinding.
6. Return route geometry, distance/profile information, warnings, and data-availability metadata.

## Frontend responsibilities

The frontend is responsible for the 3D Mars globe, camera, interaction, and visual presentation. The backend must not implement the 3D visualization.

## Initial scope

The first implementation task is scaffolding:
- Create the backend package structure.
- Define API routes and Pydantic schemas.
- Define service and algorithm interfaces.
- Add configuration and static data file placeholders.
- Add health checks, Docker setup, and basic tests.
- Ensure the API starts without downloaded datasets.

The initial scaffold must not pretend that route planning or scientific data processing is already implemented.

## Planned data categories

Potential data categories include:
- Elevation / topography.
- Slope derived from elevation.
- Terrain roughness, if a suitable source is obtained.
- Thermal information, if a suitable source is obtained.
- Geological information, if a suitable source is obtained.

These are planned categories, not a guarantee that data has been downloaded, processed, or validated.

## Constraints

- Keep the system small and understandable.
- Use a modular monolith, not microservices.
- Do not fetch large NASA datasets on every API request.
- Do not send large raw raster arrays in JSON.
- Report missing or partial data explicitly.
- Never invent scientific values, coverage, units, or dataset resolutions.
