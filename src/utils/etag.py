import hashlib
import json
import logging
from .serialization import to_serializable

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

def generate_etag(data) -> str:
    # Make sure that data is serialized first so we don't get an error in converting it.
    serialized_data = to_serializable(data)

    # Convert the data to a stable JSON string.
    JSON_string = json.dumps(serialized_data, sort_keys = True).encode("utf-8")

    # Hash the data with MD5, as it's fast.
    return hashlib.md5(JSON_string).hexdigest()
