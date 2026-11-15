# Development Plan

## Constraint

The team has a total of 24 hours for the hackathon. Prioritize a working, demonstrable workflow and avoid optional infrastructure.

The core workflow is: **elevation data → slope → cost grid → A\* → GeoJSON route with profile and data quality.** Everything else is optional and must never block it.

## Architecture decisions that shape the plan

- The backend is Python (FastAPI). A* runs on the backend over an in-memory **cost stack** (see `API_CONTRACTS.md`, "Data contract").
- Heavy rasters live in a **static data store** (S3 or any static host), never in Git. The backend downloads what it needs into local disk at startup.
- **No database in v1.** Saved routes are kept in memory. `app/database/` and `app/models/` stay in the repo but are not imported from `main.py`; the `db` service in `docker-compose.yml` moves to an optional profile.
- Every data factor is declared in `layers_registry.yaml`. Adding a factor means one registry entry plus one ingestion script, never changes to A*.
- Image tiles (HiRISE, CTX, THEMIS) are requested by the frontend directly from NASA Trek; the backend does not serve them.

## Priority order

### P0 — Application scaffold
- FastAPI application starts, with prefix `/api/v1`.
- Health endpoint works and reports per-dataset status (`datasets`, `layers`, `database_status: "disabled"`).
- API routers are registered, including the new stubs: `/site`, `/mars/traverse/curiosity`, `/mars/images/near` (all `501` until implemented).
- Pydantic v2 schemas exist for every request and response in `API_CONTRACTS.md`.
- Configuration is environment-based (`.env`, documented).
- `CORSMiddleware` is enabled with `CORS_ORIGINS` (default `http://localhost:5173`); without it the browser blocks the frontend.
- Error responses use `{code, message, details?}`; validation errors return `VALIDATION_ERROR` (422); no Python tracebacks leak.
- Docker setup is available and starts the API without a database.
- Basic tests pass.
- The application starts even if the data files are missing.

### P1 — One real terrain data path
- Identify and obtain a suitable Mars elevation dataset (planned: MSL Gale Merged DEM 1m v3, USGS). Do not download the whole 3.87 GB file; clip the study area with GDAL over HTTP range requests.
- Run `gdalinfo` and **record** its source, resolution, units, coordinate reference system, vertical datum and coverage. The CRS defines the master grid.
- Preprocess a small useful area into the master grid (planned: 5 m/px; 2 m DEM kept for the elevation profile) with a versioned script (`scripts/prepare_dem.py`).
- Compute **slope** from the DEM (and roughness, only if it is cheap).
- Create `layers_registry.yaml` with the grid and the first layers, and build `cost_stack.tif`.
- Publish the processed data to the static store, or share it locally as a fallback, and make the backend load it **once at startup**.
- Expose `GET /mars/terrain` and `GET /site` for that area, with `null` plus `data_availability` for anything missing.
- **Coordinate acceptance test:** serve `GET /mars/traverse/curiosity` and check that its points fall on the rover tracks in the HiRISE layer (error < 10 m). A ~3 km north–south offset means latitudes are mixed (planetocentric vs planetographic). Do not continue to P2 before this passes.

### P2 — Route planning
- Convert the requested region into a suitable grid window from the cost stack.
- Define valid cells and terrain costs from slope (and any other `available` layer), following the cost rules in `API_CONTRACTS.md`. Cells above `max_slope_deg` or without data are impassable.
- Implement A* (`heapq` + `numpy`, straight-line heuristic); with waypoints, run A* leg by leg and concatenate.
- Run A* in a thread (`run_in_threadpool`) if it takes more than 1–2 s.
- Convert the resulting path into GeoJSON.
- Return `metrics`, `elevation_profile` (every 10 m), `stops`, `data_quality` and `computation` (`layers_used`, `layers_unavailable`).
- Include AND thermal/epithermal neutron counts as an optional regional reference (5° cells, counts/s, source and period); do not treat them as human dose or use them as an A* cost.
- Return `NO_FEASIBLE_ROUTE` with `details.blocking_constraint` when no route satisfies the constraints; never return `completed` with fabricated data.
- Keep calculated routes in memory and expose `GET /routes/{route_id}` (max ~100 routes).
- Validate: compare DEM-derived slope with the `tilt_deg` Curiosity measured at its waypoints.

### P3 — Additional layers and polish
- Add roughness, thermal or radiation only if a suitable dataset can be obtained and processed in time. For each new layer: one registry entry, one ingestion script, one `provenance/{id}.json`, one new band in the cost stack.
  - Look for a **raw raster** first. Use decoded color tiles only as a last resort and mark them `estimated`. Visual-only tiles (HiRISE, CTX, THEMIS DayIR) never enter the cost.
  - Radiation is a **model** (Curiosity RAD calibration plus elevation correction), always marked `estimated`.
- Add `warnings` with position and `distance_m`, and clear missing-data behavior.
- Add `GET /mars/layers` generated from the registry, and `GET /mars/layers/{layer_id}/raster` for derived layers.
- Add `GET /mars/images/near` (Curiosity raw images matched by sol).
- Integrate and test the frontend workflow.
- Prepare a reliable demo.

## Endpoint priorities

| Priority | Endpoints |
|---|---|
| P0 | `GET /health`, and all other routes registered as `501` stubs |
| P1 | `GET /site`, `GET /mars/terrain`, `GET /mars/traverse/curiosity` |
| P2 | `POST /routes/plan`, `GET /routes/{route_id}` |
| P3 | `GET /mars/layers`, `GET /mars/layers/{layer_id}/raster`, `GET /mars/images/near` |

The frontend can still render the layer panel while `GET /mars/layers` is a stub, using NASA Trek directly.

## Suggested 24-hour schedule

| Elapsed time | Backend | Frontend |
|---|---|---|
| 0–2 h | Repository, scaffold, contracts, application startup, CORS, no PostgreSQL, 501 stubs (P0) | API client with `VITE_API_URL`; shows `501` as "in development" |
| 2–5 h | Obtain and inspect elevation data; run `gdalinfo`; record CRS and grid | Layer panel using NASA Trek directly |
| 5–7 h | Prepare a small region; compute slope; build the first `cost_stack.tif`; publish to the data store | Origin/destination click on the map |
| 7–10 h | `/site`, `/mars/terrain`, `/mars/traverse/curiosity`; **coordinate acceptance test** | Run the coordinate acceptance test (draw the traverse over HiRISE) |
| 10–14 h | A* and terrain cost (P2) | Draw the route on the terrain (clamped to ground) |
| 14–17 h | `POST /routes/plan` complete: GeoJSON, metrics, profile, `GET /routes/{id}` in memory | Elevation profile chart |
| 17–19 h | Additional data layer only if feasible (roughness, radiation model) | Alerts panel |
| 19–21 h | `warnings`, data quality, edge cases, `/mars/layers` | Science stops and photos (`/mars/images/near`) |
| 21–24 h | End-to-end integration, tests, demo rehearsal | UX polish, demo rehearsal |

Adjust this schedule to the team's actual progress. Do not allow optional layers to block a working elevation-to-route workflow.

## Cut lines and fallbacks

If the team falls behind, cut in this order (last item first):

1. `GET /mars/images/near`
2. `GET /mars/layers/{layer_id}/raster` and the registry-generated `/mars/layers`
3. Thermal inertia (stays `unavailable` and is declared as such)
4. Radiation model
5. Roughness

Never cut: the coordinate acceptance test, slope-based A*, `data_quality`, and honest `null` / `501` behavior.

| Risk | Fallback |
|---|---|
| Data store (S3) or CORS is not ready | Load `cost_stack.tif` from local disk (`DATA_LOCAL_DIR`); share the file by Drive/OneDrive |
| DEM clip is too large or A* is too slow | Raise the grid cell size (5 m → 8–10 m) or shrink the study area |
| No raw raster exists for a factor | Leave the layer `unavailable`; do not invent data |
| Coordinates are offset by ~3 km | Fix before anything else: planetocentric vs planetographic latitude |

## Definition of Done for the initial scaffold

- [x] Application starts locally.
- [x] Health endpoint returns a valid response with per-dataset status.
- [x] All planned route modules are registered, including `/site`, `/mars/traverse/curiosity` and `/mars/images/near`.
- [x] Request and response schemas are defined (Pydantic v2) and match `API_CONTRACTS.md`.
- [x] Unimplemented functionality returns an honest status such as 501.
- [x] Missing static data files do not prevent application startup.
- [x] Environment variables are documented.
- [x] CORS is enabled for the frontend origin.
- [ ] Docker Compose can start the API without a database.
- [x] `database_status` reports `"disabled"`.
- [x] Basic tests pass.
- [x] No fabricated scientific data is returned.

## Definition of Done for the demo

- [ ] The coordinate acceptance test passes (Curiosity points fall on HiRISE rover tracks, error < 10 m).
- [ ] A route between two clicked points is returned with GeoJSON, metrics and elevation profile.
- [ ] A route with at least one science-stop waypoint works.
- [ ] `NO_FEASIBLE_ROUTE` is returned, with its blocking constraint, for an impossible request.
- [ ] `data_quality` and `computation.layers_unavailable` correctly report missing layers.
- [ ] Every modeled value is marked `estimated`, with its source.
- [ ] `validate_dataset.py` passes: registry, cost stack and provenance files agree.
- [ ] The demo runs from a clean clone using the documented steps.

## Scope control

Do not introduce microservices, Kafka, Redis, Celery, Kubernetes, PostgreSQL/PostGIS, or a complex tile server unless a concrete requirement makes one necessary. Prefer a small, testable implementation.

Bring PostgreSQL back only if, after the hackathon, the team needs to save missions between sessions, share routes between users, or run spatial queries over many vector layers. The code in `app/database/` stays ready for that.