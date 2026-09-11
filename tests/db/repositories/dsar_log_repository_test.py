
from src.db.models.auth.dsar_log_model import DSARLogModel
from src.db.repositories.dsar_log_repository import DSARLogRepository
from src.db.models.auth.user_models import UserInternalModel
from src.utils.auth.password_utils import hash_password
from src.constants.dsar_constants import (
    DSAR_STATUS_PENDING,
    DSAR_STATUS_FULFILLED,
    DSAR_STATUS_FAILED,
    DSAR_REQUEST_EXPORT_USER_DATA,
    DSAR_REQUEST_DELETE_USER_DATA,
    DSAR_REQUEST_DELETE_USER_ACCOUNT,
)

# ---------------------------------------------------------
# DSAR LOG REPOSITORY
# ---------------------------------------------------------

class TestDSARLogRepository:

    def test_create_log_creates_pending_log(self, create_test_db):
        # We need a real user because the DSARLogModel requires user_id with a 
        # foreign key. It will check to make sure the user exists. If not,
        # it will fail to create a DSAR log.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()
        
        repo = DSARLogRepository(create_test_db)

        log = repo.create_log(
            user_id = user.id,
            request_type = DSAR_REQUEST_EXPORT_USER_DATA,
            notes = "Test note"
        )

        create_test_db.commit()

        stored_log = create_test_db.get(DSARLogModel, log.id)

        assert stored_log is not None
        assert stored_log.user_id == user.id
        assert stored_log.request_type == DSAR_REQUEST_EXPORT_USER_DATA
        assert stored_log.status == DSAR_STATUS_PENDING
        assert stored_log.notes == "Test note"
        assert stored_log.requested_at is not None
        assert stored_log.fulfilled_at is None


    def test_mark_fulfilled_updates_status_and_timestamp(self, create_test_db):
        # We need a real user because the DSARLogModel requires user_id with a 
        # foreign key. It will check to make sure the user exists. If not,
        # it will fail to create a DSAR log.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        repo = DSARLogRepository(create_test_db)

        log = repo.create_log(user.id, DSAR_REQUEST_DELETE_USER_DATA)

        repo.mark_fulfilled(log.id)

        create_test_db.commit()

        stored_log = create_test_db.get(DSARLogModel, log.id)

        assert stored_log.status == DSAR_STATUS_FULFILLED
        assert stored_log.fulfilled_at is not None
        assert stored_log.fulfilled_at > stored_log.requested_at


    def test_mark_failed_updates_status_notes_and_timestamp(self, create_test_db):
        # We need a real user because the DSARLogModel requires user_id with a 
        # foreign key. It will check to make sure the user exists. If not,
        # it will fail to create a DSAR log.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()
        repo = DSARLogRepository(create_test_db)

        log = repo.create_log(user.id, DSAR_REQUEST_DELETE_USER_ACCOUNT)

        repo.mark_failed(log.id, notes = "Operation failed")

        create_test_db.commit()

        stored_log = create_test_db.get(DSARLogModel, log.id)

        assert stored_log.status == DSAR_STATUS_FAILED
        assert stored_log.notes == "Operation failed"
        assert stored_log.fulfilled_at is None


    def test_get_logs_for_user_returns_logs_in_desc_order(self, create_test_db):
        # We need a real user because the DSARLogModel requires user_id with a 
        # foreign key. It will check to make sure the user exists. If not,
        # it will fail to create a DSAR log.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        repo = DSARLogRepository(create_test_db)

        # Create three logs with slight timestamp differences.
        repo.create_log(user.id, DSAR_REQUEST_EXPORT_USER_DATA)
        repo.create_log(user.id, DSAR_REQUEST_DELETE_USER_DATA)
        repo.create_log(user.id, DSAR_REQUEST_DELETE_USER_ACCOUNT)

        create_test_db.commit()

        logs = repo.get_logs_for_user(user.id)

        # Should be ordered by requested_at DESC.
        assert logs[0].requested_at >= logs[1].requested_at >= logs[2].requested_at

        # All logs should belong to the same user.
        assert all(log.user_id == user.id for log in logs)
