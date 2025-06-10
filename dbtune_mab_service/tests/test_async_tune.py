import requests
import time

# Define the payload for the async tune request
payload = {
    "table": "users",
    "columns": ["age", "income", "location"],
    "options": {
        "query_file": "/app/test_inputs/test.sql",
        "config_file": "/app/test_inputs/config.yaml",
        "alpha": 0.1
    }
}

# Step 1: Submit async tune request
response = requests.post("http://localhost:5050/mab/tune_async", json=payload)
response.raise_for_status()
task_id = response.json().get("task_id")
print(f"Task submitted. Task ID: {task_id}")

# Step 2: Poll for result
status_url = f"http://localhost:5050/mab/status/{task_id}"

while True:
    status_resp = requests.get(status_url)
    status_resp.raise_for_status()
    status_data = status_resp.json()

    if status_data["status"] == "done":
        print("\n✅ Suggestion received:")
        print(status_data["result"])
        break
    elif status_data["status"] == "pending":
        progress = status_data.get("progress", "?")
        print(f"⏳ Progress: {progress}")
    elif status_data["status"] == "error":
        print(f"❌ Error: {status_data.get('message', 'Unknown')}")
        break
    else:
        print("Waiting for result...")

    time.sleep(1)
