# Constants for SQLAlchemy metadata used for models.

DELIMITER_KEY = "delimiter"
DELIMITER_VALUE = ";"
IS_PRICE_KEY = "is_price"

# Tells us the delimiter when field is an array
DELIMITER_INFO_DICT = {DELIMITER_KEY: DELIMITER_VALUE}

# Tells us if numeric field is a price.
IS_PRICE_INFO_DICT = {IS_PRICE_KEY: True}