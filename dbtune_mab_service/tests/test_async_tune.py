import os
import time

import pytest
import requests


def _service_base_url():
    return os.getenv("DBTUNE_MAB_SERVICE_URL", "http://localhost:5050")


def _service_is_reachable(base_url):
    try:
        response = requests.get(f"{base_url}/docs", timeout=1.5)
        return response.status_code < 500
    except requests.RequestException:
        return False


@pytest.mark.integration
def test_async_tune_endpoint():
    base_url = _service_base_url()
    if not _service_is_reachable(base_url):
        pytest.skip(f"MAB service is not running at {base_url}")

    payload = {
        "table": "users",
        "columns": ["age", "income", "location"],
        "options": {
            "query_file": "/app/test_inputs/test.sql",
            "config_file": "/app/test_inputs/config.yaml",
            "alpha": 0.1,
        },
    }

    response = requests.post(f"{base_url}/mab/tune_async", json=payload, timeout=5)
    response.raise_for_status()
    task_id = response.json().get("task_id")
    assert task_id, "No task_id returned from async tune endpoint"

    status_url = f"{base_url}/mab/status/{task_id}"
    for _ in range(60):
        status_resp = requests.get(status_url, timeout=5)
        status_resp.raise_for_status()
        status_data = status_resp.json()
        status = status_data.get("status")

        if status == "done":
            assert "result" in status_data
            return
        if status == "error":
            pytest.fail(f"Service returned error status: {status_data}")

        time.sleep(1)

    pytest.fail("Timed out waiting for async tune completion")

