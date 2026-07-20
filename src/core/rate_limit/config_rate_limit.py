import os

# Use lowered rate limits if running the test_rate_limiting script for quicker testing.
# This script specifically tests rate limiting, so we don't want to remove it entirely.
# We also don't want to wait forever, so we just use lower limits.
#
# DEV_RATE_LIMIT only gets set in the test_rate_limiting.ps1 script, so default to false.
def _is_dev():
    return os.getenv("DEV_RATE_LIMIT", "false").lower() == "true"

# Ignore rate limiting for all standard testing via Pytest.
def _is_testing():
    return os.getenv("PYTEST_RUNNING", "false").lower() == "true"

def GLOBAL_RATE_LIMIT(): 
    if _is_testing():
        return "10000/minute"
    
    elif _is_dev():
        return "10/minute"
    
    else: 
        return "100/minute"

def HIGH_RATE_LIMIT(): 
    if _is_testing():
        return "10000/minute"
    
    elif _is_dev():
        return "20/minute"
    
    else: 
        return "200/minute"

def LOW_RATE_LIMIT(): 
    if _is_testing():
        return "10000/minute"
    
    elif _is_dev():
        return "5/minute"
    
    else: 
        return "30/minute"

def VERY_LOW_RATE_LIMIT() : 
    if _is_testing():
        return "10000/minute"
    
    else: 
        return "5/minute"