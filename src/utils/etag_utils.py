import hashlib
import json

from src.utils.serialization_utils import to_serializable
# from src.utils.log_utils import safe_debug

def generate_etag(data) -> str:
    # Make sure that data is serialized first so we don't get an error in converting it.
    serialized_data = to_serializable(data)

    # Convert the data to a stable JSON string.
    JSON_string = json.dumps(serialized_data, sort_keys = True).encode("utf-8")

    # Hash the data with MD5, as it's fast.
    return hashlib.md5(JSON_string).hexdigest()
