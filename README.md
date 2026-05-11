# dbtune

`dbtune` is a PostgreSQL auto-index tuning prototype that connects workload observation, index recommendation, and database extension capabilities into an iterative optimization loop.

## Why This Project Matters

- Reduce manual tuning effort by systematizing index tuning workflows.
- Support online evolution by continuously ingesting queries and triggering tuning logic.
- Bridge research and engineering by validating MAB (multi-armed bandit) strategies with PostgreSQL extensions.

## Project Components

- `dbtune_mab_service/`: tuning service layer built with FastAPI, Celery, and Redis.
- `dbtune_pg_mab_extension/`: PostgreSQL C extension for experimental integration.
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
```

Expected:

```json
{"status":"ok"}
```

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

- Current project version is tracked in `VERSION`, starting from `0.1.0`.
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

## Project Status (v0.1.0 Baseline)

- Available: service orchestration, health endpoint, test baseline, and versioned release workflow.
- In progress: deeper tuning algorithm integration, real workload validation, and expanded end-to-end verification.

