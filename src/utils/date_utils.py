from email.utils import format_datetime
from datetime import datetime

def http_date(dt: datetime) -> str:
    return format_datetime(dt, usegmt = True)
