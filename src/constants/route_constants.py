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

SIGNUP = "signup"
SEND_VERIFICATION = "send_verification"
VERIFY_EMAIL = "verify_email"
REQUEST_PASSWORD_RESET = "request_password_reset"
RESET_PASSWORD = "reset_password"
LOGIN = "login"
LOGOUT = "logout"
LOGOUT_ALL = "logout_all"
ACTIVE_SESSIONS = "active_sessions"
TERMINATE_SESSION = "terminate_session"
REFRESH = "refresh"
ME = "me"
EXPORT_USER_DATA = "export_user_data"

AUTH_PREFIX = f"/{AUTH}"

AUTH_SIGNUP_PREFIX = f"{AUTH_PREFIX}/{SIGNUP}"
AUTH_SEND_VERIFICATION_PREFIX = f"{AUTH_PREFIX}/{SEND_VERIFICATION}"
AUTH_VERIFY_EMAIL_PREFIX = f"{AUTH_PREFIX}/{VERIFY_EMAIL}"
AUTH_REQUEST_PASSWORD_RESET_PREFIX = f"{AUTH_PREFIX}/{REQUEST_PASSWORD_RESET}"
AUTH_RESET_PASSWORD_PREFIX = f"{AUTH_PREFIX}/{RESET_PASSWORD}"
AUTH_LOGIN_PREFIX = f"{AUTH_PREFIX}/{LOGIN}"
AUTH_LOGOUT_PREFIX = f"{AUTH_PREFIX}/{LOGOUT}"
AUTH_LOGOUT_ALL_PREFIX = f"{AUTH_PREFIX}/{LOGOUT_ALL}"
AUTH_ACTIVE_SESSIONS_PREFIX = f"{AUTH_PREFIX}/{ACTIVE_SESSIONS}"
AUTH_TERMINATE_SESSION_PREFIX = f"{AUTH_PREFIX}/{TERMINATE_SESSION}"
AUTH_REFRESH_PREFIX = f"{AUTH_PREFIX}/{REFRESH}"
AUTH_ME_PREFIX = f"{AUTH_PREFIX}/{ME}"
AUTH_EXPORT_USER_DATA_PREFIX = f"{AUTH_PREFIX}/{EXPORT_USER_DATA}"


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
