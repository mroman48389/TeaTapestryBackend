import time
from fastapi import APIRouter
from src.cache.simple_cache import cache  # adjust import if needed

router = APIRouter()

@router.get("/debug/cache")
def debug_cache():
    ''' Returns observability metrics for cache. '''
    now = time.time()

    keys_info = []
    for key, entry in cache.store.items():
        ttl_remaining = max(0, int(entry["expires_at"] - now))

        keys_info.append({
            "key": key,
            "ttl_remaining": ttl_remaining,
            "timestamp": entry["timestamp"].isoformat()
        })

    return {
        "hits": cache.hits,
        "misses": cache.misses,
        "keys": keys_info
    }
