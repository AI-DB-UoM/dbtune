# Independent Services Runbook

This repository contains three independent PostgreSQL extension + service paths:

- `MAB` (`dbtune_mab`): workload observation and index recommendation flow.
- `CoLSE` (`dbtune_colse`): cardinality estimation.
- `GrASP` (`dbtune_grasp`): semantic prefetch planning.

They can be enabled simultaneously, but they are not auto-chained into one pipeline.

## 1) Shared Prerequisites

Start stack:

```bash
docker compose up -d --build
```

Basic health checks:

```bash
curl -s http://127.0.0.1:5050/health
curl -s http://127.0.0.1:5060/health
curl -s http://127.0.0.1:5070/health
```

Enable extensions and GUCs in PostgreSQL:

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
```

Check effective values:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SHOW dbtune_mab_tuning; SHOW dbtune_colse_enabled; SHOW dbtune_grasp_enabled;"
```

## 2) MAB (Many Queries Tuning Path)

### 2.1 Send many queries

Run workload SQL through PostgreSQL (example):

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -f /path/in/container/workload.sql
```

Or run a batch from host:

```bash
psql "host=127.0.0.1 port=5438 dbname=pgdb user=pguser password=123456" -f ./dbtune_mab_service/workloads/test_workload.sql
```

### 2.2 Verify queries are being collected

```bash
docker exec aidb-redis-1 redis-cli LLEN sql_queue
docker exec aidb-redis-1 redis-cli LRANGE sql_queue 0 9
```

Inspect one queued query by hash:

```bash
docker exec aidb-redis-1 redis-cli HGETALL sql:<hash>
```

### 2.3 Trigger a manual MAB suggestion

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SELECT dbtune_mab_tune('users', ARRAY['age','income']);"
```

Current behavior note:

- MAB service currently returns a placeholder suggestion string in this integration stage.
- Query collection and trigger plumbing are available; full production-grade training integration is still evolving.

## 3) CoLSE (Cardinality Estimation Path)

Basic call:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SELECT dbtune_colse_estimate('select 1 as a');"
```

Extract only cardinality value from returned JSON text:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SELECT (dbtune_colse_estimate('select 1 as a')::jsonb ->> 'cardinality_estimate')::float AS cardinality;"
```

## 4) GrASP (Semantic Prefetch Path)

Important:

- `GrASP` returns prefetch plan + confidence.
- `GrASP` does not return cardinality in the current API contract.

### 4.1 Check mode and protocol

```bash
curl -s http://127.0.0.1:5070/grasp/info
curl -s http://127.0.0.1:5070/grasp/protocol
```

### 4.2 Basic estimate call

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SELECT dbtune_grasp_estimate('select 1 as a');"
```

Extract plan/confidence:

```bash
docker exec aidb-postgres-1 psql -U pguser -d pgdb -c "SELECT dbtune_grasp_estimate('select 1 as a')::jsonb -> 'prefetch_plan' AS prefetch_plan, (dbtune_grasp_estimate('select 1 as a')::jsonb ->> 'confidence')::float AS confidence;"
```

### 4.3 Enable real external GrASP endpoint

Update `docker-compose.yml` under `grasp_api.environment`:

```bash
GRASP_MODE=external
GRASP_EXTERNAL_ENDPOINT=http://<your-grasp-endpoint>/grasp/estimate
GRASP_TIMEOUT_MS=1500
```

Apply changes:

```bash
docker compose up -d --build grasp_api
```

Verify:

```bash
curl -s http://127.0.0.1:5070/grasp/info
```

Expected:

```json
{"mode":"external"}
```

## 5) Troubleshooting

If PostgreSQL function call succeeds but host `curl 127.0.0.1:<port>` fails:

- Check container status and mapped ports:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

- Test service reachability from PostgreSQL container network:

```bash
docker exec aidb-postgres-1 sh -lc "curl -s http://grasp_api:5070/grasp/info"
```
