from datetime import datetime

# from bandits.sim_c3ucb_vF import BanditTuner
from sql_queue.loader import SQLLoader

class TuneManager:
    def __init__(self, redis_mgr):
        self.r = redis_mgr.get_conn()
        self.tuner = BanditTuner()
        self.loader = SQLLoader(redis_mgr)

    def auto_tune(self):
        self.immediate_tune()

    def immediate_tune(self):
        # {
        #     "hash": sql_hash,
        #     "sql": data.get("sql", ""),
        #     "hit_count": int(data.get("hit_count", 0)),
        #     "timestamp": data.get("timestamp", ""),
        #     "last_seen": data.get("last_seen", ""),
        #     "attributes": json.loads(data.get("attributes", "{}")),
        # }
        sqls = self.loader.load_top_hit_count(limit=1000)

        # print(sqls)
        raw_queries = [sql["sql"] for sql in sqls]

        print("-" * 50)
        for query in raw_queries:
            print(query)
        print("-" * 50)
        # self.tuner.init(raw_queries)
        # print("The tuner is going to tune: \n", raw_queries)
        # self.tuner.train_MAB_via_dead_loop()

    def start_tuning(self, sql_hash: str, task_id: str = None):
        now = datetime.now().isoformat()
        self.r.hset("mab:tuning_status", mapping={
            "is_tuning": "true",
            "start_time": now,
            "last_updated": now,
            "current_sql_hash": sql_hash,
            "progress": "0.0"
        })
        if task_id:
            self.r.set("mab:current_task_id", task_id)

    def update_progress(self, progress: float):
        now = datetime.now().isoformat()
        self.r.hset("mab:tuning_status", mapping={
            "progress": str(progress),
            "last_updated": now
        })

    def complete_tuning(self):
        now = datetime.now().isoformat()
        self.r.hset("mab:tuning_status", mapping={
            "is_tuning": "false",
            "last_updated": now
        })

    def get_status(self):
        return self.r.hgetall("mab:tuning_status")

    def set_task_result(self, task_id: str, result: dict):
        self.r.hset(f"mab:task:{task_id}", mapping=result)

    def get_task_result(self, task_id: str):
        return self.r.hgetall(f"mab:task:{task_id}")