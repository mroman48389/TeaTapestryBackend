from src.cache.simple_cache import cache

def test_debug_cache_endpoint(client):
    # Prime the cache with something

    cache.set("test_key", {"hello": "world"})

    response = client.get("/debug/cache")
    assert response.status_code == 200

    data = response.json()

    # Basic structure
    assert "hits" in data
    assert "misses" in data
    assert "keys" in data

    # Should contain our test key
    keys = data["keys"]
    
    assert any(entry["key"] == "test_key" for entry in keys)

    # TTL remaining should be >= 0
    entry = next(e for e in keys if e["key"] == "test_key")

    assert entry["ttl_remaining"] >= 0
    assert "timestamp" in entry
