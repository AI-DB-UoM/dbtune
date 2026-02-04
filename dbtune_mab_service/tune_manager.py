from datetime import datetime

# from bandits.sim_c3ucb_vF import BanditTuner
from sql_queue.loader import SQLLoader
from tabulate import tabulate

class TuneManager:
    def __init__(self, redis_mgr, tune_gap: int = 10):
        self.r = redis_mgr.get_conn()
        # self.tuner = BanditTuner()
        self.loader = SQLLoader(redis_mgr)
        self.tune_gap = tune_gap
        self.current_sql_index = 0

    # TODO how to trigger tune
    # TODO 1. A simple threshold
    # TODO 2. Query distribution has been changed
    # TODO 3. Data drift
    # TODO 4. Model prediction gets different outputs
    def auto_tune(self, is_sql_useful):

        print(f"[auto_tune] {is_sql_useful} current index:{self.current_sql_index} total tune threshold:{self.tune_gap}")  # or use logging
        
        if is_sql_useful:
            self.current_sql_index += 1
    
        if self.current_sql_index < self.tune_gap:
            return
        self.immediate_tune()
        self.current_sql_index = 0


    def immediate_tune(self):
        sqls = self.loader.load_top_hit_count(limit=10)

        trimmed_sqls = []
        for entry in sqls:
            trimmed_sqls.append({
                "sql": entry["sql"][:40] + "..." if len(entry["sql"]) > 80 else entry["sql"],
                "hit_count": entry["hit_count"],
                "timestamp": entry["timestamp"][:19],
                "last_seen": entry["last_seen"][:19]
            })
        print(tabulate(trimmed_sqls, headers="keys", tablefmt="grid"))

        # print(sqls)
        raw_queries = [sql["sql"] for sql in sqls]

        # print("-" * 50)
        # for query in raw_queries:
        #     print(query)
        # print("-" * 50)
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