# Development Plan

## Constraint

The team has a total of 24 hours for the hackathon. Prioritize a working, demonstrable workflow and avoid optional infrastructure.

## Priority order

### P0 — Application scaffold
- FastAPI application starts.
- Health endpoint works.
- API routers are registered.
- Pydantic schemas exist.
- Configuration is environment-based.
- Docker setup is available.
- Basic tests pass.

### P1 — One real terrain data path
- Identify and obtain a suitable Mars elevation dataset.
- Record its source, resolution, units, coordinate reference, and coverage.
- Preprocess a small useful area.
- Make the processed data accessible to the backend.
- Expose a terrain/elevation query for that area.

### P2 — Route planning
- Convert the requested region into a suitable grid.
- Define valid cells and terrain costs.
- Implement A*.
- Convert the resulting path into GeoJSON.
- Return distance, profile, and data-quality information.

### P3 — Additional layers and polish
- Add roughness or thermal information only if a suitable dataset can be obtained and processed in time.
- Add warnings and clear missing-data behavior.
- Integrate and test the frontend workflow.
- Prepare a reliable demo.

## Suggested 24-hour schedule

| Elapsed time | Focus |
|---|---|
| 0–2 h | Repository, scaffold, contracts, application startup |
| 2–5 h | Obtain and inspect elevation data |
| 5–7 h | Prepare a small region and analytical products |
| 7–10 h | Terrain/elevation API integration |
| 10–14 h | A* and terrain cost |
| 14–17 h | GeoJSON route response and profile |
| 17–19 h | Additional data layer only if feasible |
| 19–21 h | Warnings, data quality, edge cases |
| 21–24 h | End-to-end integration, tests, demo |

Adjust this schedule to the team's actual progress. Do not allow optional layers to block a working elevation-to-route workflow.

## Definition of Done for the initial scaffold

- [ ] Application starts locally.
- [ ] Health endpoint returns a valid response.
- [ ] All planned route modules are registered.
- [ ] Request and response schemas are defined.
- [ ] Unimplemented functionality returns an honest status such as 501.
- [ ] Missing datasets do not prevent application startup.
- [ ] Environment variables are documented.
- [ ] Docker Compose can start the API and database.
- [ ] Basic tests pass.
- [ ] No fabricated scientific data is returned.

## Scope control

Do not introduce microservices, Kafka, Redis, Celery, Kubernetes, or a complex tile server unless a concrete requirement makes one necessary. Prefer a small, testable implementation.
