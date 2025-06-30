import json
from datetime import datetime

class SQLLoader:
    def __init__(self, redis_mgr=None):
        self.r = redis_mgr.get_conn()

    def _parse_sql_record(self, sql_hash):
        key = f"sql:{sql_hash}"
        data = self.r.hgetall(key)
        if not data:
            return None
        return {
            "hash": sql_hash,
            "sql": data.get("sql", ""),
            "hit_count": int(data.get("hit_count", 0)),
            "timestamp": data.get("timestamp", ""),
            "last_seen": data.get("last_seen", ""),
            "attributes": json.loads(data.get("attributes", "{}")),
        }

    def load_all(self):
        hashes = self.r.lrange("sql_queue", 0, -1)
        return [r for h in hashes if (r := self._parse_sql_record(h))]

    def load_latest_seen(self, limit=100):
        sqls = self.load_all()
        sqls.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
        return sqls[:limit]

    # def load_top_hit_count(self, limit=100):
    #     sqls = self.load_all()
    #     sqls.sort(key=lambda x: x.get("hit_count", 0), reverse=True)
    #     return sqls[:limit]
    # def load_top_hit_count(self, limit=100):
    #     sqls = self.load_all()
    #     sqls.sort(key=lambda x: (
    #         -x.get("hit_count", 0),
    #         x.get("last_seen", "")
    #     ), reverse=False)
    #     return sqls[:limit]

    def _parse_iso(self, s: str):
        try:
            return datetime.fromisoformat(s)
        except:
            return datetime.min

    def load_top_hit_count(self, limit=100):
        sqls = self.load_all()
        sqls.sort(key=lambda x: (
            -x.get("hit_count", 0),
            -self._parse_iso(x.get("last_seen", "")).timestamp()  # 时间降序
        ))
        return sqls[:limit]


    def load_latest_created(self, limit=100):
        sqls = self.load_all()
        sqls.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return sqls[:limit]
