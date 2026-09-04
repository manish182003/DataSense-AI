import os
import json
import time
from typing import Optional, Any

class SystemCache:
    """Production Redis / In-Memory cache manager with TTL."""
    def __init__(self):
        self.memory_store = {}
        self.redis_client = None
        
        # Optional Redis connection
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        try:
            import redis
            client = redis.Redis(host=redis_host, port=redis_port, socket_timeout=1)
            client.ping()
            self.redis_client = client
        except Exception:
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val.decode("utf-8"))
            except Exception:
                pass

        # Fallback to memory store
        item = self.memory_store.get(key)
        if item:
            value, expires_at = item
            if expires_at is None or time.time() < expires_at:
                return value
            else:
                del self.memory_store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass

        expires_at = time.time() + ttl if ttl else None
        self.memory_store[key] = (value, expires_at)

    def clear(self):
        self.memory_store.clear()

system_cache = SystemCache()
