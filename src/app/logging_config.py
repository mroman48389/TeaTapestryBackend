import logging

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
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addFilter(RequestIdFilter())
    root.handlers = [handler]