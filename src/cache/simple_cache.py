import time
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any
import sentry_sdk
from sentry_sdk import metrics

class CacheEntry(TypedDict):
    value: Any
    expires_at: float
    timestamp: datetime

class SimpleCache:
    # ttl = Time to Live. This is the length of time it takes for 
    # something cached to expire from the moment it's stored. After this
    # time, SimpleCache treats that something as missing. This prevents
    # stale data from living forever. 300 seconds gives 5 minutes by default.
    #
    # store is a dict that holds the cached items. Each item's format is
    #     "key": { "value": ..., "expires_at": ..., "timestamp": ... }
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.store: dict[str, CacheEntry] = {}

        # Observability
        self.hits = 0
        self.misses = 0

    def get(self, key) -> Optional[CacheEntry]:
        with sentry_sdk.start_span(op = "cache.get", name = "cache lookup"):

            # Try to get the cached item via its key.
            entry = self.store.get(key)

            # If nothing is there, increment misses before returning None.
            if entry is None:
                self.misses += 1

                # Capture miss metrics for Sentry.
                metrics.count("cache.miss", 1) 
                sentry_sdk.capture_message("cache_miss", level = "info")

                return None

            # Delete the cache item and increment misses if it's expired.
            if time.time() > entry["expires_at"]:
                self.misses += 1
                del self.store[key]

                # Capture expiration metrics for Sentry.
                metrics.count("cache.expired", 1) 
                sentry_sdk.capture_message("cache_expired", level = "info")

                return None

            # If the cached item exists and is not expired, increment hits and
            # return the cached item.
            self.hits += 1

            # Capture hit metrics for Sentry.
            metrics.count("cache.hit", 1) 
            sentry_sdk.capture_message("cache_hit", level = "info")

            return entry

    def set(self, key, value):
        with sentry_sdk.start_span(op = "cache.set", name = "cache store"):
            expires_at = time.time() + self.ttl
            self.store[key] = {
                "value": value,
                "expires_at": expires_at,
                "timestamp": datetime.now(timezone.utc)
            }

            # Track cache size.
            metrics.gauge("cache.size", len(self.store)) 

    def clear(self):
        self.store.clear()

        # Reset counters
        self.hits = 0
        self.misses = 0

cache = SimpleCache()