import sys
from pathlib import Path

# This part is needed because we run this script as python verify_settings.py from the root.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Add src/ to the FRONT of sys.path
sys.path.insert(0, str(SRC))

from src.core.config import settings # noqa: E402

def main():
    print("=== Environment Loading Test ===")
    print("ENVIRONMENT:", settings.environment)
    print("DATABASE_URL:", settings.database_url)
    print("JWT_SECRET:", settings.jwt_secret)
    print("JWT_EXPIRES_IN:", settings.jwt_expires_in)
    print("CORS_ORIGINS:", settings.cors_origins)
    print("SENTRY_DSN:", settings.sentry_dsn)
    print("RATE_LIMIT:", settings.rate_limit)
    print("CACHE_URL:", settings.cache_url)
    print("LOG_LEVEL:", settings.log_level)
    print("API_BASE_URL:", settings.api_base_url)
    print("SUPABASE_URL:", settings.supabase_url)
    print("SUPABASE_SERVICE_ROLE_KEY:", settings.supabase_service_role_key)

if __name__ == "__main__":
    main()
