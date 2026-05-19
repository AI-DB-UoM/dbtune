import json
import math
import os
import subprocess

import pytest


PG_CONTAINER = os.getenv("DBTUNE_PG_CONTAINER", "aidb-postgres-1")
PG_USER = os.getenv("DBTUNE_PG_USER", "pguser")
PG_DB = os.getenv("DBTUNE_PG_DB", "pgdb")


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _docker_ready() -> bool:
    probe = _run_cmd(["docker", "exec", PG_CONTAINER, "true"])
    return probe.returncode == 0


def _psql(sql: str, tuples_only: bool = True) -> str:
    cmd = [
        "docker",
        "exec",
        PG_CONTAINER,
        "psql",
        "-U",
        PG_USER,
        "-d",
        PG_DB,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        cmd.extend(["-t", "-A"])
    cmd.extend(["-c", sql])
    out = _run_cmd(cmd)
    if out.returncode != 0:
        raise RuntimeError(
            f"psql failed\nsql={sql}\nstdout={out.stdout}\nstderr={out.stderr}"
        )
    return out.stdout.strip()


def _explain_plan_rows(sql: str) -> float:
    payload = _psql(f"EXPLAIN (FORMAT JSON) {sql}")
    parsed = json.loads(payload)
    return float(parsed[0]["Plan"]["Plan Rows"])


def _supports_colse_enabled_guc() -> bool:
    probe = _psql("SELECT current_setting('dbtune.colse_enabled', true) IS NOT NULL;")
    return probe.strip().lower() == "t"


@pytest.mark.integration
def test_colse_small_volume_cardinality_feedback():
    if not _docker_ready():
        pytest.skip(
            f"docker container '{PG_CONTAINER}' is not reachable in this environment"
        )

    # Ensure extension + runtime flags are enabled.
    _psql("CREATE EXTENSION IF NOT EXISTS dbtune_colse;", tuples_only=False)
    if not _supports_colse_enabled_guc():
        pytest.skip(
            "dbtune.colse_enabled is unavailable in the running PostgreSQL image; rebuild/restart the extension image first"
        )

    _psql("ALTER SYSTEM SET dbtune.colse_enabled = 'on';", tuples_only=False)
    _psql(
        "ALTER SYSTEM SET dbtune.colse_service_url = 'http://colse_api:5060/colse/estimate';",
        tuples_only=False,
    )
    _psql("SELECT pg_reload_conf();", tuples_only=False)

    # Ingest a small synthetic dataset.
    _psql(
        """
        DROP TABLE IF EXISTS colse_users;
        CREATE TABLE colse_users (
          user_id INT PRIMARY KEY,
          age INT NOT NULL,
          income INT NOT NULL,
          city_group INT NOT NULL
        );
        INSERT INTO colse_users
        SELECT
          g,
          18 + (g % 55),
          25000 + ((g * 211) % 120000),
          g % 9
        FROM generate_series(1, 1200) AS g;
        ANALYZE colse_users;
        """,
        tuples_only=False,
    )

    test_queries = [
        "SELECT * FROM colse_users WHERE age > 30 AND income < 70000",
        "SELECT * FROM colse_users WHERE age BETWEEN 25 AND 40 AND city_group IN (1,2,3)",
        "SELECT * FROM colse_users WHERE income >= 90000",
    ]

    feedback_rows: list[str] = []
    for q in test_queries:
        estimate_payload = _psql(f"SELECT dbtune_colse_estimate($${q}$$);")
        parsed = json.loads(estimate_payload)

        assert parsed.get("status") == "ok", f"CoLSE call failed: payload={parsed}"
        estimate = float(parsed["cardinality_estimate"])
        assert estimate >= 0.0, f"Invalid negative estimate from CoLSE: {estimate}"

        actual = int(_psql(f"SELECT COUNT(*) FROM ({q}) AS subq;"))
        ratio = (estimate / actual) if actual > 0 else math.inf
        abs_err = abs(estimate - actual)

        feedback_rows.append(
            (
                f"query={q}\n"
                f"  estimate={estimate:.3f}, actual={actual}, "
                f"abs_error={abs_err:.3f}, est/actual={ratio:.3f}"
            )
        )

    # Validate planner replacement modes for a simple single-table query.
    plan_query = test_queries[1]

    estimate_payload = _psql(f"SELECT dbtune_colse_estimate($${plan_query}$$);")
    estimate = float(json.loads(estimate_payload)["cardinality_estimate"])

    _psql("ALTER SYSTEM SET dbtune.colse_enabled = 'off';", tuples_only=False)
    _psql("SELECT pg_reload_conf();", tuples_only=False)
    native_rows = _explain_plan_rows(plan_query)

    _psql("ALTER SYSTEM SET dbtune.colse_enabled = 'on';", tuples_only=False)
    _psql(
        "ALTER SYSTEM SET dbtune.colse_service_url = 'http://colse_api:5060/colse/estimate';",
        tuples_only=False,
    )
    _psql("SELECT pg_reload_conf();", tuples_only=False)
    replaced_rows = _explain_plan_rows(plan_query)

    assert (
        abs(replaced_rows - estimate) <= 1.0
    ), f"planner rows should follow CoLSE estimate (rows={replaced_rows}, estimate={estimate})"

    # Fail-open: if CoLSE endpoint is unreachable, planner should keep PG native estimate.
    _psql(
        "ALTER SYSTEM SET dbtune.colse_service_url = 'http://127.0.0.1:9/colse/estimate';",
        tuples_only=False,
    )
    _psql("SELECT pg_reload_conf();", tuples_only=False)
    failopen_rows = _explain_plan_rows(plan_query)
    assert (
        failopen_rows == native_rows
    ), f"planner should fall back to native estimate on CoLSE failure ({failopen_rows} vs {native_rows})"

    print("\n[CoLSE small-volume feedback]")
    for row in feedback_rows:
        print(row)
    print("\n[CoLSE planner replacement]")
    print(
        f"query={plan_query}\n"
        f"  native_rows={native_rows:.3f}\n"
        f"  colse_estimate={estimate:.3f}\n"
        f"  replaced_rows={replaced_rows:.3f}\n"
        f"  failopen_rows={failopen_rows:.3f}"
    )
