from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.db.models.auth.dsar_log_model import DSARLogModel
from src.maintenance_services.dsar_retention_service import DSARRetentionService
from src.constants.dsar_constants import REQUEST_EXPORT_USER_DATA, STATUS_PENDING


class TestDSARRetentionService:

    def test_delete_old_logs_deletes_only_old_logs(self, create_test_db):
        service = DSARRetentionService(create_test_db)

        user_id = uuid4()

        old_log = DSARLogModel(
            user_id = user_id,
            request_type = REQUEST_EXPORT_USER_DATA,
            status = STATUS_PENDING,
            requested_at = datetime.now(timezone.utc) - timedelta(days = 400),
        )
        create_test_db.add(old_log)

        recent_log = DSARLogModel(
            user_id = user_id,
            request_type = REQUEST_EXPORT_USER_DATA,
            status = STATUS_PENDING,
            requested_at =datetime.now(timezone.utc) - timedelta(days = 10),
        )
        create_test_db.add(recent_log)

        create_test_db.commit()

        num_deleted_logs = service.delete_old_logs()
        assert num_deleted_logs == 1

        remaining_logs = (
            create_test_db.query(DSARLogModel)
            .filter(DSARLogModel.user_id == user_id)
            .all()
        )

        assert len(remaining_logs) == 1
        assert remaining_logs[0].id == recent_log.id
