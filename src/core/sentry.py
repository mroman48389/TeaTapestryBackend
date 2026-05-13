import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from src.core.config import settings

# dsn: Where to send events.
#
# integrations: Instrument SQLAlchemy so we can see DB queries in traces and
#     breadbrumbs. FastAPI is done automatically now.
#
# send_default_pii: Set to false so we don't send personally identifiable information
#     like IP addresses, cookies, user identifiers, request headers.
#
# traces_sample_rate: Control performance tracing where 0.0 = disabled and 
#     1.0 = capture all traces.
def init_sentry():
    sentry_sdk.init(
        dsn = settings.sentry_dsn, # where to send events
        integrations = [
            SqlalchemyIntegration(),
        ],
        send_default_pii = False,
        traces_sample_rate = 0.0,  # will adjust  later
        enable_metrics = True,      # Lets us do metric.incr, .set
    )
