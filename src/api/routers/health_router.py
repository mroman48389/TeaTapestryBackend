from fastapi import APIRouter, Request

from src.app.health_services import HealthService
from src.core.rate_limit.config_rate_limit import HIGH_RATE_LIMIT, LOW_RATE_LIMIT
from src.core.rate_limit.setup_rate_limit import rate_limiter

import logging

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

# Define group of routes with health as their base path and health
# for documentation grouping.
router = APIRouter(prefix = "/health", tags = ["health"])

health_service = HealthService()

@router.get("")
@rate_limiter.limit(HIGH_RATE_LIMIT)
async def health(request: Request):
    # Basic smoke test to tell us if the app is reachable at all.
    return {"status": "ok"}
    
@router.get("/connections")
@rate_limiter.limit(LOW_RATE_LIMIT)
async def health_connections(request: Request):
    # Smoke test to tell us if resources are reachable.
    return health_service.check_all_connections()