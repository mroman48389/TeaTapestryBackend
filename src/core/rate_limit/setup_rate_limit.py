from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.rate_limit.config_rate_limit import GLOBAL_RATE_LIMIT

rate_limiter = Limiter(
    key_func = get_remote_address, 
    default_limits=[GLOBAL_RATE_LIMIT]
)