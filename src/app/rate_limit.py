import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Use lowered rate limits if running the test_rate_limiting script for quicker testing.
def _is_dev():
    return os.getenv("DEV_RATE_LIMIT", "false").lower() == "true"

def GLOBAL_RATE_LIMIT(): return "10/minute"  if _is_dev() else "100/minute"
def HIGH_RATE_LIMIT():   return "20/minute"  if _is_dev() else "200/minute"
def LOW_RATE_LIMIT():    return "5/minute"   if _is_dev() else "30/minute"

rate_limiter = Limiter(
    key_func = get_remote_address, 
    default_limits=[GLOBAL_RATE_LIMIT]
)