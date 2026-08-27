from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.db.models.auth.dsar_log_model import DSARLogModel

from src.constants.dsar_constants import RETENTION_DAYS

# DSAR logs must be purged at least after every 12 months.
# TODO (Staging/Production):
# TeaTapestryBackend runs on Fly.io, so this local Windows Task Scheduler job
# will NOT run in staging or production. When merging this feature, create a
# Fly.io-compatible scheduled job (e.g., a Fly Machine with a cron-like
# schedule or a separate maintenance process) that runs this script on a
# daily cadence. This ensures DSAR retention cleanup happens automatically
# in deployed environments.
class DSARRetentionService:
    def __init__(self, session: Session):
        self.session = session

    def delete_old_logs(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days = RETENTION_DAYS)

        # Use synchronize_session = False because this bulk delete runs outside any
        # request/response cycle and we don't need ORM state synchronization. It avoids
        # expensive session updates and is the recommended mode for maintenance tasks.
        num_deleted_logs = (
            self.session.query(DSARLogModel)
            .filter(DSARLogModel.requested_at < cutoff)
            .delete(synchronize_session = False)
        )

        self.session.commit()

        return num_deleted_logs
