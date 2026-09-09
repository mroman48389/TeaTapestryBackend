from datetime import datetime, timedelta, timezone

from src.db.models.auth.dsar_log_model import DSARLogModel
from src.maintenance_services.dsar_retention_service import DSARRetentionService
from src.db.models.auth.user_models import UserInternalModel
from src.utils.auth.password_utils import hash_password
from src.constants.dsar_constants import DSAR_REQUEST_EXPORT_USER_DATA, DSAR_STATUS_PENDING


class TestDSARRetentionService:

    def test_delete_old_logs_deletes_only_old_logs(self, create_test_db):
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

        service = DSARRetentionService(create_test_db)

        old_log = DSARLogModel(
            user_id = user.id,
            request_type = DSAR_REQUEST_EXPORT_USER_DATA,
            status = DSAR_STATUS_PENDING,
            requested_at = datetime.now(timezone.utc) - timedelta(days = 400),
        )
        create_test_db.add(old_log)

        recent_log = DSARLogModel(
            user_id = user.id,
            request_type = DSAR_REQUEST_EXPORT_USER_DATA,
            status = DSAR_STATUS_PENDING,
            requested_at =datetime.now(timezone.utc) - timedelta(days = 10),
        )
        create_test_db.add(recent_log)

        create_test_db.commit()

        num_deleted_logs = service.delete_old_logs()
        create_test_db.commit()
        
        assert num_deleted_logs == 1

        remaining_logs = (
            create_test_db.query(DSARLogModel)
            .filter(DSARLogModel.user_id == user.id)
            .all()
        )

        assert len(remaining_logs) == 1
        assert remaining_logs[0].id == recent_log.id
