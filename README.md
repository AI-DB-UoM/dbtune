# dbtune

`dbtune` is a PostgreSQL auto-index tuning prototype that connects workload observation, index recommendation, and database extension capabilities into an iterative optimization loop.

## Why This Project Matters

- Reduce manual tuning effort by systematizing index tuning workflows.
- Support online evolution by continuously ingesting queries and triggering tuning logic.
- Bridge research and engineering by validating MAB (multi-armed bandit) strategies with PostgreSQL extensions.

## Research Lineage

This repository is an integration-focused PostgreSQL prototype. It brings together several research threads from the DANAIS Lab and adapts them into a single extension-oriented stack.

### MAB / HMAB Tuning Line

- Related works:
  - `ICDE 2021`: DBA bandits: Self-driving index tuning under ad-hoc, analytical workloads with safety guarantees
  - `VLDB 2022`: HMAB: Self-Driving Hierarchy of Bandits for Integrated Physical Database Design Tuning
  - `TKDE 2023`: No DBA? No regret! Multi-armed bandits for index tuning of analytical and HTAP workloads with provable guarantees
  - `ICDM 2024`: Warm-Starting Contextual Bandits under Latent Reward Scaling
  - `SIGMOD 2026`: AgentTune: An Agent-Based Large Language Model Framework for Database Knob Tuning
- Original public code bases:
  - `DBA Bandits`: https://github.com/malingaperera/DBABandits
  - `HMAB`: https://github.com/malingaperera/HMAB
- In this repository:
  - `dbtune_mab_service/`
  - `dbtune_pg_mab_extension/`

### CoLSE Cardinality Estimation Line

- Related works:
  - `ICDE 2026`: CoLSE: A Lightweight and Robust Hybrid Learned Model for Single-Table Cardinality Estimation using Joint CDF
  - `VLDB 2025`: Cardinality Estimation for Similarity Search on High-Dimensional Data Objects: The Impact of Reference Objects
- Original code base:
  - No public code link is listed on the DANAIS publications page for CoLSE at the time of writing.
- In this repository:
  - `colse_service/`
  - `dbtune_pg_colse_extension/`

### GrASP Semantic Prefetching Line

- Related works:
  - `VLDB 2024`: SeLeP: Learning Based Semantic Prefetching for Exploratory Database Workloads
  - `ICDE 2026`: Generalizable Address-aware Semantic Prefetching for Scalable Transactional and Analytical Workloads
- Original public code bases:
  - `SeLeP`: https://github.com/fzirak/SeLeP
  - No public code link is listed on the DANAIS publications page for the ICDE 2026 GrASP paper at the time of writing.
- In this repository:
  - `grasp_service/`
  - `dbtune_pg_grasp_extension/`

### Publication Index

- DANAIS Lab publications page: https://danais-lab.com/

## Project Components

- `dbtune_mab_service/`: tuning service layer built with FastAPI, Celery, and Redis.
- `dbtune_pg_mab_extension/`: PostgreSQL C extension for experimental integration.
- `colse_service/`: CoLSE estimator service API (current stub model for integration flow).
- `dbtune_pg_colse_extension/`: PostgreSQL C extension bridge for CoLSE calls.
- `grasp_service/`: GrASP estimator service API (current stub model for integration flow).
- `dbtune_pg_grasp_extension/`: PostgreSQL C extension bridge for GrASP calls.
- `docker-compose.yml`: one-command local stack for PostgreSQL, Redis, API, and worker.

## Service Independence (Important)

`dbtune_mab`, `dbtune_colse`, and `dbtune_grasp` are independent services/modules in this repository.

- They can be enabled at the same time.
- They do not form an automatic end-to-end pipeline by default.
- `GrASP` does **not** return cardinality estimates in the current interface; cardinality is provided by `CoLSE`.

Detailed runbook: [`docs/independent-services-runbook.md`](docs/independent-services-runbook.md)

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
curl -s http://127.0.0.1:5070/health
```

Expected:

```json
{"status":"ok"}
```

## Enable HMAB, CoLSE, and GrASP (Independent, Can Run Together)

Run the following after the stack is up:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS dbtune_mab;"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS dbtune_colse;"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS dbtune_grasp;"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_mab_tuning = 'on';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_colse_enabled = 'on';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_grasp_enabled = 'on';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_mab_service_url = 'http://mab_api:5050/mab/';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_colse_service_url = 'http://colse_api:5060/colse/estimate';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET dbtune_grasp_service_url = 'http://grasp_api:5070/grasp/estimate';"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT pg_reload_conf();"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_colse_estimate('select 1 as a');"
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_grasp_estimate('select 1 as a');"
```

Expected results:
- `dbtune_mab_tuning`, `dbtune_colse_enabled`, and `dbtune_grasp_enabled` are set to `on`.
- `dbtune_colse_estimate(...)` returns JSON-like text containing `status":"ok"` when the CoLSE service is reachable.
- `dbtune_grasp_estimate(...)` returns JSON-like text containing `status":"ok"` when the GrASP service is reachable.

## How to Use HMAB, CoLSE, and GrASP (Detailed)

### HMAB (MAB) usage

Use this path when you want to ingest many workload queries and request index recommendations.

1. Feed many queries through PostgreSQL:

```bash
psql "host=127.0.0.1 port=5438 dbname=pgdb user=pguser password=123456" -f ./dbtune_mab_service/workloads/test_workload.sql
```

2. Confirm queries are collected in Redis:

```bash
docker exec aidb-redis-1 redis-cli LLEN sql_queue
docker exec aidb-redis-1 redis-cli LRANGE sql_queue 0 9
docker exec aidb-redis-1 redis-cli HGETALL sql:<hash>
```

3. Trigger a manual suggestion from PostgreSQL:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_mab_tune('users', ARRAY['age','income']);"
```

4. Optional API trigger (service endpoint):

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

Notes:
- In the current integration stage, the MAB suggestion response is placeholder-style text.
- Workload capture and trigger plumbing are available; production-grade end-to-end tuning logic is still evolving.

### CoLSE usage (cardinality estimation)

Use this path when you need cardinality estimates.

1. Basic estimate call:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_colse_estimate('select 1 as a');"
```

2. Extract numeric cardinality from JSON text:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT (dbtune_colse_estimate('select 1 as a')::jsonb ->> 'cardinality_estimate')::float AS cardinality;"
```

3. Batch style example from SQL:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "WITH q(sql) AS (VALUES ('select 1 as a'), ('select * from pg_class')) SELECT sql, (dbtune_colse_estimate(sql)::jsonb ->> 'cardinality_estimate')::float AS cardinality FROM q;"
```

### GrASP usage (semantic prefetch)

Use this path when you need a prefetch plan and confidence score.

Important:
- GrASP currently does not return cardinality.
- Cardinality comes from CoLSE.

1. Basic estimate call:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_grasp_estimate('select 1 as a');"
```

2. Extract prefetch plan and confidence:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -v ON_ERROR_STOP=1 -c "SELECT dbtune_grasp_estimate('select 1 as a')::jsonb -> 'prefetch_plan' AS prefetch_plan, (dbtune_grasp_estimate('select 1 as a')::jsonb ->> 'confidence')::float AS confidence;"
```

### GrASP service modes

The GrASP service supports two runtime modes:
- `stub`: built-in lightweight estimator for integration testing.
- `external`: forwards requests to a real GrASP-compatible endpoint.

Environment variables:

```bash
GRASP_MODE=auto|stub|external
GRASP_EXTERNAL_ENDPOINT=http://host:port/grasp/estimate
GRASP_TIMEOUT_MS=1500
```

Default behavior:
- `GRASP_MODE=auto` uses `external` when `GRASP_EXTERNAL_ENDPOINT` is set, otherwise falls back to `stub`.

Protocol helpers:
- `GET /grasp/info` returns current mode (`stub` or `external`).
- `GET /grasp/protocol` returns request/response contract and compatibility keys.

Enable external mode example:

1. Update `docker-compose.yml` under `grasp_api.environment`:

```bash
GRASP_MODE=external
GRASP_EXTERNAL_ENDPOINT=http://<your-grasp-endpoint>/grasp/estimate
GRASP_TIMEOUT_MS=1500
```

2. Recreate the GrASP service:

```bash
docker compose up -d --build grasp_api
```

3. Verify mode:

```bash
curl -s http://127.0.0.1:5070/grasp/info
```

## Local Development

### Run tests

```bash
pytest -q
```

Recommended integration checks for HMAB + CoLSE:

```bash
# Combined smoke test with explicit output
pytest -q -s test/test_hmab_colse_smoke.py

# Small-volume HMAB workflow
pytest -q -s test/test_hmab_small_volume.py

# Small-volume CoLSE cardinality feedback
pytest -q -s test/test_colse_small_volume.py
```

Notes:

- Integration tests are skipped when external dependencies (PostgreSQL/Redis/services) are unavailable.
- Unit/configuration tests run by default.

## Versioning and Release Policy

- Current project version is tracked in `VERSION` (current: `0.1.4`).
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

## Project Status (v0.1.4)

- Available: service orchestration, health endpoints (`5050` + `5060` + `5070`), hmab + CoLSE + GrASP extension integration, and versioned release workflow.
- Available: CI quality gates for Python/C plus PostgreSQL extension build and install verification.
- In progress: replacing the CoLSE and GrASP stubs with full model integration and expanding real workload validation coverage.
