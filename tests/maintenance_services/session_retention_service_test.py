from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.db.models.auth.session_token_model import SessionTokenModel
from src.maintenance_services.session_retention_service import SessionRetentionService
from src.db.models.auth.user_models import UserInternalModel
from src.utils.auth.password_utils import hash_password
from src.constants.session_constants import SESSION_RETENTION_DAYS


class TestSessionRetentionService:

    def test_delete_old_sessions_deletes_only_old_sessions(self, create_test_db):
        # We need a real user because the DSARRetentionService requires user_id with a 
        # foreign key. It will check to make sure the user exists. If not,
        # it will fail to create a DSAR log.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        service = SessionRetentionService(create_test_db)

        cutoff = datetime.now(timezone.utc) - timedelta(days = SESSION_RETENTION_DAYS)

        # Old expired session (expires_at < cutoff)
        old_expired_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "old_expired_token_hash",
            refresh_token_id = uuid4(),
            expires_at = cutoff - timedelta(days = 10), # expired
            revoked_at = None,
        )
        create_test_db.add(old_expired_session)

        # Old revoked session (revoked_at < cutoff)
        old_revoked_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "old_revoked_token_hash",
            refresh_token_id = uuid4(),
            expires_at = cutoff + timedelta(days = 5),  # not expired
            revoked_at = cutoff - timedelta(days = 10),  # revoked 
        )
        create_test_db.add(old_revoked_session)

        # Recent valid session
        recent_valid_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "recent_valid_token_hash",
            refresh_token_id = uuid4(),
            expires_at = cutoff + timedelta(days = 30),
            revoked_at = None,
        )
        create_test_db.add(recent_valid_session)

        # Recent revoked session
        recent_revoked_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "recent_revoked_token_hash",
            refresh_token_id = uuid4(),
            expires_at = cutoff + timedelta(days = 30),
            revoked_at = cutoff + timedelta(days = 1),
        )
        create_test_db.add(recent_revoked_session)

        create_test_db.commit()

        num_deleted_sessions = service.delete_old_sessions()
        create_test_db.commit()

        # Only the two old session tokens should be deleted. The
        # other two should remain.
        assert num_deleted_sessions == 2

        remaining_sessions = (
            create_test_db.query(SessionTokenModel)
            .filter(SessionTokenModel.user_id == user.id)
            .all()
        )

        assert len(remaining_sessions) == 2
        remaining_ids = {s.id for s in remaining_sessions}

        assert recent_valid_session.id in remaining_ids
        assert recent_revoked_session.id in remaining_ids
