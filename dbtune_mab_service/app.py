import re
from pydantic import BaseModel
from celery.result import AsyncResult
from celery import Celery
import redis
from fastapi import FastAPI, HTTPException
from mab_interface import suggest_index
from redis_manager import RedisManager
from tune_manager import TuneManager
from sql_queue.receiver import SQLReceiver

app = FastAPI()

r = redis.Redis(host="redis", port=6379, db=0)  # TODO use redis_mgr

redis_mgr = RedisManager.get_instance(host="redis", port=6379, db=0)
receiver = SQLReceiver(redis_mgr)
tune_mgr = TuneManager(redis_mgr)

celery = Celery("mab", broker="redis://redis:6379/0", backend="redis://redis:6379/0")


class MABRequest(BaseModel):
    table: str
    columns: list[str]
    options: dict = {}


class MABQueryRequest(BaseModel):
    query: str | None = None


class MABResponse(BaseModel):
    status: str
    suggestion: str
    task_id: str


def _parse_tune_call(query: str) -> tuple[str, list[str]] | None:
    # Example: SELECT dbtune_mab_tune('hmab_users', ARRAY['age','income']);
    pattern = r"dbtune_mab_tune\s*\(\s*'([^']+)'\s*,\s*array\s*\[(.*?)\]\s*\)"
    match = re.search(pattern, query, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    table = match.group(1).strip()
    cols_raw = match.group(2)
    columns = [c.strip().strip('"').strip("'") for c in cols_raw.split(",")]
    columns = [c for c in columns if c]
    return table, columns


def _infer_from_recent_sql() -> tuple[str, list[str], list[str]] | None:
    sqls = tune_mgr.loader.load_top_hit_count(limit=100)
    recent_queries = []
    for entry in sqls:
        sql = entry.get("sql", "").strip()
        if not sql:
            continue
        recent_queries.append(sql)
        parsed = _parse_tune_call(sql)
        if parsed:
            table, columns = parsed
            return table, columns, recent_queries
    return None


def _recommend_with_existing_mab(
    table: str, columns: list[str], query_pool: list[str]
) -> str:
    # Use the existing MAB interface path instead of constructing SQL in API layer.
    return suggest_index(table=table, columns=columns, config={}, query=query_pool)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/mab/tune_async")
def mab_tune_async(req: MABRequest):
    print(f"[RECEIVED QUERY] {req}")  # or use logging
    # if False:  # Always false, so no task is created
    #     task = run_mab_task.delay(req.dict())
    #     return {"task_id": task.id}
    return {"task_id": "this_is_the_task_id"}  # Dummy ID to simulate success
    # task = run_mab_task.delay(req.dict())
    # return {"task_id": task.id}


@app.post("/mab/query")
def mab_tune_query(req: MABQueryRequest):

    print(f"[RECEIVED REQUEST] {req}")  # or use logging
    print(f"[RECEIVED QUERY] {req.query}")  # or use logging

    if not req.query:
        raise HTTPException(status_code=400, detail="query is required")

    sql = req.query.lower()
    is_sql_useful = receiver.receive(sql)
    tune_mgr.auto_tune(is_sql_useful)
    return {"suggestion": "Return current status??"}  # Dummy ID to simulate success
    # task = run_mab_task.delay(req.dict())
    # return {"task_id": task.id}


@app.post("/mab/tune")
def dbtune_mab_tune(req: MABQueryRequest):

    print(f"[RECEIVED REQUEST] {req}")  # or use logging
    print(f"[RECEIVED QUERY] {req.query}")  # or use logging

    if not req.query:
        raise HTTPException(status_code=400, detail="query is required")

    sql_lower = req.query.lower().strip()
    recent_queries = [
        entry.get("sql", "").strip()
        for entry in tune_mgr.loader.load_top_hit_count(limit=100)
        if entry.get("sql", "").strip()
    ]

    parsed = _parse_tune_call(req.query)
    if parsed:
        table, columns = parsed
        return {
            "suggestion": _recommend_with_existing_mab(table, columns, recent_queries)
        }

    if sql_lower == "select dbtune_mab_tune();":
        print("Triger MAB tuning")
        receiver.receive(sql_lower)
        tune_mgr.immediate_tune()
        inferred = _infer_from_recent_sql()
        if inferred:
            table, columns, inferred_queries = inferred
            return {
                "suggestion": _recommend_with_existing_mab(
                    table, columns, inferred_queries
                )
            }

    inferred = _infer_from_recent_sql()
    if inferred:
        table, columns, inferred_queries = inferred
        return {
            "suggestion": _recommend_with_existing_mab(table, columns, inferred_queries)
        }

    raise HTTPException(
        status_code=422,
        detail=(
            "Cannot infer tuning target. Use "
            "dbtune_mab_tune('<table>', ARRAY['col1','col2']) to request recommendation."
        ),
    )


@app.get("/mab/status/{task_id}")
def mab_status(task_id: str):
    try:
        result = AsyncResult(task_id, app=celery)
        progress = r.get(f"progress:{task_id}")
        progress = progress.decode() if progress else "unknown"

        if result.ready():
            return {"status": "done", "result": result.result}

        return {"status": "pending", "progress": progress}
    except Exception as e:
        print("Exception:", e)
        raise HTTPException(status_code=500, detail=str(e))
