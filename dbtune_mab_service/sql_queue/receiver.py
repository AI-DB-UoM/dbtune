from redis_manager import RedisManager
import hashlib
import json
from datetime import datetime
import csv

class SQLReceiver:
    def __init__(self, redis_mgr=None):
        self.r = redis_mgr.get_conn()
        self.black_list_start, self.black_list_keyword = self._load_blacklist()

    def _load_blacklist(self, csv_path="./resource/dbtune_sql_black_list.csv"):
        start_list = []
        keyword_list = []
        with open(csv_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["type"] == "START":
                    start_list.append(row["sql_keyword"].lower())
                elif row["type"] == "KEYWORD":
                    keyword_list.append(row["sql_keyword"].lower())
        return start_list, keyword_list

    def normalize_sql(self, sql):
        return sql.strip().lower()

    def hash_sql(self, sql):
        return hashlib.sha256(sql.encode()).hexdigest()

    def is_seen(self, sql_hash):
        return self.r.sismember("sql_seen", sql_hash)

    def store_sql(self, sql: str, sql_hash: str, attributes: dict):
        key = f"sql:{sql_hash}"
        now = datetime.now().isoformat()

        self.r.sadd("sql_seen", sql_hash)
        self.r.rpush("sql_queue", sql_hash)
        self.r.hset(key, mapping={
            "sql": sql,
            "timestamp": now,
            "last_seen": now,
            "hit_count": 1,
            "attributes": json.dumps(attributes)
        })
        print(f"[NEW] Stored SQL: {sql}")

    def _sql_filter(self, sql):
        if not (sql.startswith("select") or sql.startswith("with")):
            return False

        # Check START list
        for bad_start in self.black_list_start:
            if sql.startswith(bad_start):
                return False

        # Check KEYWORD list
        for keyword in self.black_list_keyword:
            if keyword in sql:
                return False

        return True

    def receive(self, raw_sql):
        sql = self.normalize_sql(raw_sql)

        if not self._sql_filter(sql):
            print(f"Query '{sql}' cannot be added into the pool.")
            return False

        sql_hash = self.hash_sql(sql)

        print(sql, sql_hash)

        if self.is_seen(sql_hash):
            print("Duplicate SQL. Updating metadata.")
            key = f"sql:{sql_hash}"
            self.r.hincrby(key, "hit_count", 1)
            self.r.hset(key, "last_seen", datetime.now().isoformat())
            # return
        else:
            attributes = {
                "is_sampled": False,
                "is_similar": False
            }

            self.store_sql(sql, sql_hash, attributes)
            print(f"Stored SQL: {sql}")

        # sqls = self.get_all_sql_in_queue()
        # for item in sqls:
        #     print(f"SQL: {item['sql']}")
        #     print(f"Hit Count: {item['hit_count']}")
        #     print(f"Last Seen: {item['last_seen']}")
        #     print(f"Attributes: {item['attributes']}")
        #     print("-" * 50)
        return True

    def get_all_sql_in_queue(self):
        hashes = self.r.lrange("sql_queue", 0, -1)
        results = []

        for h in hashes:
            key = f"sql:{h}"
            data = self.r.hgetall(key)
            if data:
                data["attributes"] = json.loads(data.get("attributes", "{}"))
                results.append(data)

        return results
