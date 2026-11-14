# Architecture

## Architectural style

Use a **modular monolith**: one FastAPI application with clear internal boundaries. This is appropriate for the 24-hour hackathon scope and avoids the operational overhead of microservices.

## High-level flow

```text
NASA / scientific datasets
          |
          v
Offline ingestion and preprocessing
          |
          +----> Raster files / processed data products
          |
          +----> PostgreSQL + PostGIS metadata and geometries
                         |
                         v
                    FastAPI
                         |
                         v
                      Frontend
                (3D Mars visualization)
```

The ingestion and preprocessing pipeline is planned separately from normal API request handling. API requests should read prepared products rather than repeatedly downloading and processing source datasets.

## Suggested package responsibilities

```text
app/
├── api/
│   └── routes/       # HTTP endpoints only
├── algorithms/       # A*, terrain cost, risk analysis
├── database/         # Database setup and repositories
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic request and response models
├── services/         # Application and domain services
├── utils/            # Small shared utilities
├── config.py         # Environment-based configuration
└── main.py           # FastAPI application entry point

data/
├── raw/              # Original source datasets (not committed)
├── processed/        # Prepared analytical datasets (not committed)
└── visual/           # Generated visual products (not committed)

scripts/              # Dataset ingestion and preprocessing commands
tests/                # Automated tests
```

This is a suggested initial structure. Inspect the existing repository before creating or moving files.

## Layer boundaries

### API
- Parse HTTP input.
- Validate requests using Pydantic.
- Call services.
- Return response models and appropriate HTTP status codes.
- Do not implement pathfinding, raster calculations, or SQL queries here.

### Schemas
- Define request and response contracts.
- Validate types, ranges, and required fields.
- Do not contain business logic.

### Services
- Coordinate application workflows.
- Load data through repositories or data-access services.
- Call algorithms when needed.
- Translate unavailable data into explicit application-level outcomes.

### Algorithms
- Implement reusable computation such as A* and terrain-cost evaluation.
- Avoid HTTP and database dependencies.
- Accept well-defined data structures and return computation results.

### Database
- Own SQLAlchemy configuration, models, and repository/data-access code.
- Do not assume a final Mars spatial reference identifier until it has been selected and validated.

### Scripts and data
- Handle source-data ingestion and offline preprocessing.
- Keep large raster products outside JSON API responses.
- Store source metadata, units, coordinate reference information, and processing details.

## Initial implementation rule

The initial scaffold should define modules and interfaces without implementing scientific processing or route finding. The API must start even if `data/` contains no datasets.
