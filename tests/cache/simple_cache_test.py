import logging
from src.cache.simple_cache import SimpleCache

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

def test_cache_miss_increments_misses():
    cache = SimpleCache(ttl_seconds = 300)

    assert cache.get("missing") is None
    assert cache.misses == 1

def test_cache_hit_increments_hits():
    cache = SimpleCache(ttl_seconds = 300)
    cache.set("a", 123)

    entry = cache.get("a")
    
    assert entry is not None
    assert entry["value"] == 123
    assert cache.hits == 1

def test_cache_expires():
    cache = SimpleCache(ttl_seconds = 0)
    cache.set("a", 123)

    assert cache.get("a") is None
    assert cache.misses == 1

def test_cache_clears():
    cache = SimpleCache(ttl_seconds = 300)
    cache.set("a", 123)
    cache.get("a")
    cache.clear()

    assert cache.store == {}
    assert cache.hits == 0
    assert cache.misses == 0
