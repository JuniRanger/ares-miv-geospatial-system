# API Contracts

This document describes the intended initial REST API. During scaffolding, create routes and schemas but do not implement the scientific calculations or route-finding engine.

Base prefix: `/api`

## Endpoints

| Method | Endpoint | Purpose | Initial scaffold behavior |
|---|---|---|---|
| GET | `/health` | Check API availability | Return application status |
| GET | `/mars/layers` | List known data layers | Return configured layer metadata; unavailable layers must be marked unavailable |
| GET | `/mars/texture` | Retrieve a global visual texture | Return 404/503 if no generated texture exists |
| GET | `/mars/elevation` | Query elevation at a coordinate | Return 501 until implemented |
| GET | `/mars/terrain` | Query terrain measurements | Return 501 until implemented |
| GET | `/mars/layers/{layer_id}/raster` | Retrieve a raster visualization | Return 404 if the requested generated file does not exist |
| GET | `/mars/layers/{layer_id}/data` | Retrieve vector features | Return an empty GeoJSON FeatureCollection only if that is the documented behavior; otherwise report unavailable |
| POST | `/routes/plan` | Request a route | Return 501 until route planning is implemented |
| GET | `/routes/{route_id}` | Retrieve a saved route | Return 404 when no such route exists |

The initial layer-list response includes the planned categories described in the
project overview, each marked unavailable. Unknown source, unit, resolution, and
coordinate-reference metadata is null; these entries do not assert that a dataset
has been obtained or validated. A missing texture returns 404, and unavailable
vector data returns 503 rather than an invented empty feature collection.

Do not add a tile-server endpoint unless the team explicitly chooses to implement it.

## Coordinate conventions

API request objects should use named fields:

```json
{
  "latitude": -4.5,
  "longitude": 137.4
}
```

GeoJSON geometry coordinates must use:

```json
[137.4, -4.5]
```

This example is illustrative only. The project's Mars coordinate convention, reference system, longitude direction, and datum must be explicitly selected before real geospatial calculations are implemented.

## Route request example

```json
{
  "origin": {
    "latitude": -4.5,
    "longitude": 137.4
  },
  "destination": {
    "latitude": -4.6,
    "longitude": 137.5
  },
  "preferences": {
    "avoid_steep_slopes": true,
    "avoid_rough_terrain": true,
    "consider_thermal_data": true
  }
}
```

## Route response shape

```json
{
  "route_id": "example-route-id",
  "status": "completed",
  "distance_km": null,
  "estimated_duration_min": null,
  "risk_level": "unknown",
  "geometry": {
    "type": "LineString",
    "coordinates": []
  },
  "elevation_profile": [],
  "warnings": [],
  "data_quality": {
    "elevation": "unavailable",
    "roughness": "unavailable",
    "thermal": "unavailable"
  }
}
```

This is a contract illustration, not a real route result. Do not return `completed` with fabricated route data. The final response model may evolve as implementation decisions are made.

## Terrain response shape

```json
{
  "latitude": -4.5,
  "longitude": 137.4,
  "elevation_m": null,
  "slope_degrees": null,
  "roughness": null,
  "thermal_inertia": null,
  "data_availability": {
    "elevation": false,
    "slope": false,
    "roughness": false,
    "thermal": false
  }
}
```

All measurements are nullable because datasets may be missing or have incomplete coverage. Units and value interpretation must be based on verified source metadata.

## Error response

Use a consistent error shape:

```json
{
  "error": {
    "code": "DATASET_UNAVAILABLE",
    "message": "The requested dataset is not available."
  }
}
```

Use appropriate HTTP status codes:
- `200`: successful request.
- `400`: malformed request.
- `404`: requested resource does not exist.
- `422`: request validation failed.
- `500`: unexpected server error.
- `503`: required service or data resource is unavailable.
- `501`: endpoint is intentionally not implemented yet.

## Contract rules

- Define Pydantic v2 models for requests and responses.
- Keep examples clearly illustrative.
- Do not fabricate measurements, distances, route geometry, or data availability.
- Document changes to endpoint paths or response shapes here.
