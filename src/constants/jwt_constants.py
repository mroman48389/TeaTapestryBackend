# TODO: Set this in environment later.
# Signing key, known only be the backend. Keep safe to avoid token 
# forging.
JWT_SECRET_KEY = "CHANGE_THIS_IN_PRODUCTION"
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_LIFETIME_MINUTES = 15
REFRESH_TOKEN_LIFETIME_DAYS = 7