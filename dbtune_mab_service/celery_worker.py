from celery import Celery
import redis
import time
from db_tools.query_loader import QueryLoader
from configs.read_configs import read_configs
from mab_interface import suggest_index

celery = Celery(
    "celery_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

r = redis.Redis(host="redis", port=6379, db=0)

@celery.task
def run_mab_task(payload):
    task_id = run_mab_task.request.id
    table = payload['table']
    columns = payload['columns']

    options = payload['options'] or {}

    config = read_configs(options)
    query = QueryLoader.load_query_workloads(options)

    suggestion = suggest_index(table, columns, config, query)

    for i in range(0, 101, 1):
        print(f"[DEBUG] progress:{task_id}", f"{i}%")

        r.set(f"progress:{task_id}", f"{i}%")
        time.sleep(1)

    r.set(f"progress:{task_id}", "done")
    return f"CREATE INDEX ON {table} ({', '.join(columns)})"
