import os
import logging
from logging import Handler
from logging.handlers import RotatingFileHandler

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | request_id=%(request_id)s | %(message)s"
)

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # If request_id wasn't provided, avoid KeyError
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True

def configure_logging():
    # Console handler is always enabled.
    handler_console = logging.StreamHandler()
    handler_console.setFormatter(logging.Formatter(LOG_FORMAT))
    handler_console.addFilter(RequestIdFilter())

    handlers: list[Handler] = [handler_console]

    ENV_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") 

    # File handler is only enabled in development.
    if ENV_DEVELOPMENT == "development":
        os.makedirs("logs", exist_ok = True)

        # Automatically refresh the logs. logs/backend.log will never
        # exceed 5 MB. If it does, it becomes backend.log.1, 
        # backend.log.2, etc. up to 3 logs. The oldest is deleted first.
        handler_file = RotatingFileHandler(
            "logs/backend.log",
            maxBytes = 5_000_000,  
            backupCount = 3        
        )
        handler_file.setFormatter(logging.Formatter(LOG_FORMAT))
        handler_file.addFilter(RequestIdFilter())

        handlers.append(handler_file)

    # Root logger.
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = handlers

    # Enable SQLAlchemy engine logging (safe, no parameters logged)
    # Did this so we can run a PowerShell script to detect N+1 problems.
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if ENV_DEVELOPMENT == "development":
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)
    sqlalchemy_logger.propagate = True