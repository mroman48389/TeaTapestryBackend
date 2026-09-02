from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.db.models.auth.session_token_model import SessionTokenModel
from src.constants.session_constants import SESSION_RETENTION_DAYS

# Session tokens must be purged after they have been expired or revoked
# for at least SESSION_RETENTION_DAYS.
# TODO (Staging/Production):
# TeaTapestryBackend runs on Fly.io, so this local Windows Task Scheduler job
# will NOT run in staging or production. When merging this feature, create a
# Fly.io-compatible scheduled job (e.g., a Fly Machine with a cron-like
# schedule or a separate maintenance process) that runs this script on a
# daily cadence. This ensures session token retention cleanup happens
# automatically in deployed environments and prevents long-term storage of
# authentication metadata (IP address, user agent, refresh token identifiers).
class SessionRetentionService:
    def __init__(self, session: Session):
        self.session = session

    def delete_old_sessions(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days = SESSION_RETENTION_DAYS)

        # Delete sessions that were expired or revoked once they are 
        # SESSION_RETENTION_DAYS days old
        old_sessions = (
            self.session.query(SessionTokenModel)
            .filter(
                or_(
                    SessionTokenModel.expires_at < cutoff,
                    and_(
                        SessionTokenModel.revoked_at != None,
                        SessionTokenModel.revoked_at < cutoff
                    )
                )
            )
        )

        num_old_expired_revoked_sessions = old_sessions.count()

        old_sessions.delete(synchronize_session = False)

        self.session.commit()

        return num_old_expired_revoked_sessions
