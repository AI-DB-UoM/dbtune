
from pydantic import BaseModel
from celery.result import AsyncResult
from celery import Celery
import redis
from fastapi import FastAPI, HTTPException
from mab_interface import suggest_index
from celery_worker import run_mab_task
from redis_manager import RedisManager
from tune_manager import TuneManager
from sql_queue.receiver import SQLReceiver

app = FastAPI()

r = redis.Redis(host="redis", port=6379, db=0) # TODO use redis_mgr

redis_mgr = RedisManager.get_instance(host="redis", port=6379, db=0)
receiver = SQLReceiver(redis_mgr)
tune_mgr = TuneManager(redis_mgr)

celery = Celery(
    "mab",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0" 
)

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

# @app.post("/mab/tune", response_model=MABResponse)
# def mab_tune(req: MABRequest):
#     options = req.options or {}

#     suggestion = suggest_index(req.table, req.columns, options, [])
#     return MABResponse(status="ok", suggestion=suggestion, task_id="1")

@app.post("/mab/tune_async")
def mab_tune_async(req: MABRequest):
    print(f"[RECEIVED QUERY] {req}")  # or use logging
    # if False:  # Always false, so no task is created
    #     task = run_mab_task.delay(req.dict())
    #     return {"task_id": task.id}
    return {"task_id": "noop"}  # Dummy ID to simulate success
    # task = run_mab_task.delay(req.dict())
    # return {"task_id": task.id}

@app.post("/mab/query")
def mab_tune_query(req: MABQueryRequest):

    print(f"[RECEIVED REQUEST] {req}")  # or use logging
    print(f"[RECEIVED QUERY] {req.query}")  # or use logging

    # if False:  # Always false, so no task is created
    #     task = run_mab_task.delay(req.dict())
    #     return {"task_id": task.id}

    # TODO filter out queries that are not relate to the db schema.

    receiver.receive(req.query)
    tune_mgr.auto_tune()
    return {"suggestion": "Return current status??"}  # Dummy ID to simulate success
    # task = run_mab_task.delay(req.dict())
    # return {"task_id": task.id}


@app.post("/mab/tune")
def dbtune_mab_tune(req: MABQueryRequest):

    print(f"[RECEIVED REQUEST] {req}")  # or use logging
    print(f"[RECEIVED QUERY] {req.query}")  # or use logging

    if req.query.lower() == "select dbtune_mab_tune();":
        print("Triger MAB tuning")
        tune_mgr.immediate_tune()

    return {"suggestion": "CREATE INDEX [IF NOT EXISTS] index_name ON table_name(column1, column2, ...);"}  # Dummy ID to simulate success


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
