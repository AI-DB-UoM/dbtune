# base_db.py
import abc

class BaseDB(abc.ABC):
    def __init__(self, config):
        self.config = config
        self.conn = None

    @abc.abstractmethod
    def connect(self):
        pass

    def close(self):
        if self.conn:
            self.conn.close()

    def execute(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                return cur.fetchall()
            except Exception:
                return None

    def execute_one(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
