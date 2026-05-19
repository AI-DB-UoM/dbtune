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


@pytest.mark.integration
def test_hmab_and_colse_smoke_outputs():
    if not _docker_ready():
        pytest.skip(
            f"docker container '{PG_CONTAINER}' is not reachable in this environment"
        )

    # Enable two extensions and wire service URLs.
    _psql("CREATE EXTENSION IF NOT EXISTS dbtune_mab;", tuples_only=False)
    _psql("CREATE EXTENSION IF NOT EXISTS dbtune_colse;", tuples_only=False)
    _psql("ALTER SYSTEM SET dbtune_mab_tuning = 'on';", tuples_only=False)
    _psql("ALTER SYSTEM SET dbtune_colse_enabled = 'on';", tuples_only=False)
    _psql(
        "ALTER SYSTEM SET dbtune_mab_service_url = 'http://mab_api:5050/mab/';",
        tuples_only=False,
    )
    _psql(
        "ALTER SYSTEM SET dbtune_colse_service_url = 'http://colse_api:5060/colse/estimate';",
        tuples_only=False,
    )
    _psql("SELECT pg_reload_conf();", tuples_only=False)

    # Prepare HMAB table and generate a lightweight workload.
    _psql(
        """
        DROP TABLE IF EXISTS hmab_users;
        CREATE TABLE hmab_users (
          user_id INT PRIMARY KEY,
          age INT NOT NULL,
          income INT NOT NULL,
          location TEXT NOT NULL
        );
        INSERT INTO hmab_users
        SELECT
          g,
          18 + (g % 55),
          30000 + ((g * 137) % 90000),
          'loc_' || (g % 7)
        FROM generate_series(1, 500) AS g;
        ANALYZE hmab_users;
        """,
        tuples_only=False,
    )
    for i in range(10):
        _psql(
            f"""
            SELECT user_id, age, income
            FROM hmab_users
            WHERE age > {20 + i}
              AND income < {45000 + (i * 1200)};
            """,
            tuples_only=False,
        )

    hmab_suggestion = _psql(
        "SELECT dbtune_mab_tune('hmab_users', ARRAY['age', 'income']);"
    )
    assert "CREATE INDEX" in hmab_suggestion.upper()

    # Prepare CoLSE table and collect estimate-vs-actual outputs.
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
    colse_query = (
        "SELECT * FROM colse_users WHERE age BETWEEN 25 AND 40 AND city_group IN (1,2,3)"
    )
    estimate_payload = _psql(f"SELECT dbtune_colse_estimate($${colse_query}$$);")
    parsed = json.loads(estimate_payload)
    assert parsed.get("status") == "ok"
    estimate = float(parsed["cardinality_estimate"])
    actual = int(_psql(f"SELECT COUNT(*) FROM ({colse_query}) AS subq;"))
    abs_err = abs(estimate - actual)
    ratio = (estimate / actual) if actual > 0 else math.inf

    print("\n[Smoke: HMAB]")
    print(f"suggestion={hmab_suggestion}")
    print("\n[Smoke: CoLSE]")
    print(
        "query="
        f"{colse_query}\n"
        f"estimate={estimate:.3f}, actual={actual}, abs_error={abs_err:.3f}, est/actual={ratio:.3f}"
    )
