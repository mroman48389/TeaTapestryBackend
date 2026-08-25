from src.core.env import IS_RUNNING_TESTS, USE_DEV_RATE_LIMIT

# Use lowered rate limits if running the test_rate_limiting script for quicker testing.
# This script specifically tests rate limiting, so we don't want to remove it entirely.
# We also don't want to wait forever, so we just use lower limits.

def GLOBAL_RATE_LIMIT(): 
    if IS_RUNNING_TESTS: # pragma: no cover
        return "10000/minute"
    
    elif USE_DEV_RATE_LIMIT: # pragma: no cover
        return "10/minute"
    
    else: # pragma: no cover
        return "100/minute"

def HIGH_RATE_LIMIT(): 
    if IS_RUNNING_TESTS: # pragma: no cover
        return "10000/minute"
    
    elif USE_DEV_RATE_LIMIT: # pragma: no cover
        return "20/minute"
    
    else:  # pragma: no cover
        return "200/minute"

def LOW_RATE_LIMIT(): 
    if IS_RUNNING_TESTS: # pragma: no cover
        return "10000/minute"
    
    elif USE_DEV_RATE_LIMIT: # pragma: no cover
        return "5/minute"
    
    else: # pragma: no cover
        return "30/minute"

def VERY_LOW_RATE_LIMIT() : 
    if IS_RUNNING_TESTS: # pragma: no cover
        return "10000/minute"
    
    else:  # pragma: no cover
        return "5/minute"

def LOWEST_RATE_LIMIT():
    if IS_RUNNING_TESTS: # pragma: no cover
        return "10000/minute"
    
    else:  # pragma: no cover
        return "1/minute"