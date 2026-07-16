API_V1_PREFIX = "/api/v1"


# ---------------------------------------------------------
# user tea profiles
# ---------------------------------------------------------

USER_TEA_PROFILE_NOTES = "user_tea_profile_notes"
USER_TEA_PROFILE_NOTES_PREFIX = f"{API_V1_PREFIX}/{USER_TEA_PROFILE_NOTES}"


# ---------------------------------------------------------
# tea profiles
# ---------------------------------------------------------

TEA_PROFILES = "tea_profiles"
TEA_PROFILES_PREFIX = f"{API_V1_PREFIX}/{TEA_PROFILES}"


# ---------------------------------------------------------
# auth
# ---------------------------------------------------------

AUTH = "auth"

SIGN_UP = "signup"
LOGIN = "login"
LOGOUT = "logout"
REFRESH = "refresh"
ME = "me"

AUTH_PREFIX = f"/{AUTH}"

AUTH_SIGNUP_PREFIX = f"{AUTH_PREFIX}/{SIGN_UP}"
AUTH_LOGIN_PREFIX = f"{AUTH_PREFIX}/{LOGIN}"
AUTH_LOGOUT_PREFIX = f"{AUTH_PREFIX}/{LOGOUT}"
AUTH_REFRESH_PREFIX = f"{AUTH_PREFIX}/{REFRESH}"
AUTH_ME_PREFIX = f"{AUTH_PREFIX}/{ME}"


# ---------------------------------------------------------
# health
# ---------------------------------------------------------

HEALTH = "health"

CONNECTIONS = "connections"

HEALTH_PREFIX = f"/{HEALTH}"

HEALTH_CONNECTIONS_PREFIX = f"{HEALTH_PREFIX}/{CONNECTIONS}"


# ---------------------------------------------------------
# debug
# ---------------------------------------------------------

DEBUG = "debug"

CACHE = "cache"

DEBUG_PREFIX = f"/{DEBUG}"

DEBUG_CACHE_PREFIX = f"{DEBUG_PREFIX}/{CACHE}"
