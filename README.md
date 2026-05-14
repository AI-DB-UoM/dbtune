# dbtune

`dbtune` is a PostgreSQL auto-index tuning prototype that connects workload observation, index recommendation, and database extension capabilities into an iterative optimization loop.

## Why This Project Matters

- Reduce manual tuning effort by systematizing index tuning workflows.
- Support online evolution by continuously ingesting queries and triggering tuning logic.
- Bridge research and engineering by validating MAB (multi-armed bandit) strategies with PostgreSQL extensions.

## Project Components

- `dbtune_mab_service/`: tuning service layer built with FastAPI, Celery, and Redis.
- `dbtune_pg_mab_extension/`: PostgreSQL C extension for experimental integration.
- `colse_service/`: CoLSE estimator service API (current stub model for integration flow).
- `dbtune_pg_colse_extension/`: PostgreSQL C extension bridge for CoLSE calls.
- `docker-compose.yml`: one-command local stack for PostgreSQL, Redis, API, and worker.

## Quick Start (Docker)

### 1) Start services

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

### 2) Health check

```bash
curl -s http://127.0.0.1:5050/health
curl -s http://127.0.0.1:5060/health
```

Expected:

```json
{"status":"ok"}
```

## Enable hmab + CoLSE Together

Run the following after the stack is up:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS dbtune_mab;"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS dbtune_colse;"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_mab_tuning = 'on';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_colse_enabled = 'on';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_mab_service_url = 'http://mab_api:5050/mab/';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_colse_service_url = 'http://colse_api:5060/colse/estimate';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT pg_reload_conf();"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_colse_estimate('select 1 as a');"
```

Expected:
- `dbtune_mab_tuning` and `dbtune_colse_enabled` both show `on`.
- `dbtune_colse_estimate(...)` returns JSON-like text containing `status":"ok"` when the CoLSE service is reachable.

### 3) Trigger a tuning request (example)

```bash
curl -s -X POST http://127.0.0.1:5050/mab/tune_async \
  -H 'Content-Type: application/json' \
  -d '{
    "table": "users",
    "columns": ["age", "income"],
    "options": {
      "query_file": "/app/test_inputs/test.sql",
      "config_file": "/app/test_inputs/config.yaml"
    }
  }'
```

## Local Development

### Run tests

```bash
pytest -q
```

Notes:

- Integration tests are skipped when external dependencies (PostgreSQL/Redis/services) are unavailable.
- Unit/configuration tests run by default.

## Versioning and Release Policy

- Current project version is tracked in `VERSION` (current: `0.1.3`).
- Semantic Versioning (SemVer):
  - `MAJOR`: incompatible changes
  - `MINOR`: backward-compatible features
  - `PATCH`: backward-compatible fixes
- For every version update, also update:
  - `VERSION`
  - `CHANGELOG.md`
  - This README if user-facing behavior changes

## Changelog

- See [CHANGELOG.md](CHANGELOG.md) for release-by-release changes.
- Prefer small, verifiable increments for each version to keep rollbacks easy.

## Project Status (v0.1.3)

- Available: service orchestration, health endpoints (`5050` + `5060`), hmab + CoLSE dual extension integration, and versioned release workflow.
- Available: CI quality gates for Python/C plus PostgreSQL extension build and install verification.
- In progress: replacing the CoLSE stub with full model integration and expanding real workload validation coverage.
