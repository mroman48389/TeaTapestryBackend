from src.utils.session_utils import get_session_cm  
from src.maintenance_services.dsar_retention_service import DSARRetentionService

def main():
    
    with get_session_cm() as session:
        service = DSARRetentionService(session)

        num_logs_deleted = service.delete_old_logs()

        print(f"DSAR cleanup complete. Deleted {num_logs_deleted} old logs.")

if __name__ == "__main__":
    main()
