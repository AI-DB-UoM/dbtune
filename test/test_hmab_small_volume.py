import os
import subprocess

import pytest


PG_CONTAINER = os.getenv("DBTUNE_PG_CONTAINER", "aidb-postgres-1")
REDIS_CONTAINER = os.getenv("DBTUNE_REDIS_CONTAINER", "aidb-redis-1")
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


def _redis_len(key: str) -> int:
    out = _run_cmd(["docker", "exec", REDIS_CONTAINER, "redis-cli", "LLEN", key])
    if out.returncode != 0:
        raise RuntimeError(f"redis LLEN failed: {out.stderr}")
    return int(out.stdout.strip())


@pytest.mark.integration
def test_hmab_small_volume_workflow():
    if not _docker_ready():
        pytest.skip(
            f"docker container '{PG_CONTAINER}' is not reachable in this environment"
        )

    # Ensure extension + runtime flags are enabled.
    _psql("CREATE EXTENSION IF NOT EXISTS dbtune_mab;", tuples_only=False)
    _psql("ALTER SYSTEM SET dbtune_mab_tuning = 'on';", tuples_only=False)
    _psql(
        "ALTER SYSTEM SET dbtune_mab_service_url = 'http://mab_api:5050/mab/';",
        tuples_only=False,
    )
    _psql("SELECT pg_reload_conf();", tuples_only=False)

    # Ingest a small synthetic dataset.
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

    before = _redis_len("sql_queue")

    # Generate a number of unique workload queries.
    for i in range(20):
        age_threshold = 20 + i
        income_threshold = 45000 + (i * 1500)
        _psql(
            f"""
            SELECT user_id, age, income
            FROM hmab_users
            WHERE age > {age_threshold}
              AND income < {income_threshold};
            """,
            tuples_only=False,
        )

    after = _redis_len("sql_queue")
    added = after - before
    assert added >= 10, (
        "Expected HMAB workload ingestion to enqueue many new SQL statements "
        f"(before={before}, after={after}, added={added})."
    )

    # Request a recommendation from the HMAB extension entrypoint.
    suggestion = _psql(
        "SELECT dbtune_mab_tune('hmab_users', ARRAY['age', 'income']);"
    )
    suggestion_upper = suggestion.upper()
    assert "CREATE INDEX" in suggestion_upper, (
        "HMAB recommendation response did not include an index statement. "
        f"response={suggestion}"
    )

