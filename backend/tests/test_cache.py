import time
from app.core.redis_cache import SystemCache

def test_cache_set_and_get():
    cache = SystemCache()
    cache.set("test_key", {"data": 123}, ttl=10)
    res = cache.get("test_key")
    assert res is not None
    assert res["data"] == 123

def test_cache_expiration():
    cache = SystemCache()
    cache.set("expire_key", "value", ttl=1)
    time.sleep(1.1)
    res = cache.get("expire_key")
    assert res is None
