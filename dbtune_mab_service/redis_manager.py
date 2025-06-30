import redis

class RedisManager:
    _instance = None

    def __init__(self, host='localhost', port=6379, db=0, decode_responses=True):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=decode_responses)

    @classmethod
    def get_instance(cls, **kwargs):
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    def get_conn(self):
        return self.redis
