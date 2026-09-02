from src.utils.session_utils import get_session_cm
from src.maintenance_services.session_retention_service import SessionRetentionService


def main():

    with get_session_cm() as session:
        service = SessionRetentionService(session)

        num_sessions_deleted = service.delete_old_sessions()

        print(f"Session cleanup complete. Deleted {num_sessions_deleted} expired or revoked sessions.")


if __name__ == "__main__":
    main()
