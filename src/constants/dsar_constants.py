DSAR_REQUEST_EXPORT_USER_DATA = "export_user_data"
DSAR_REQUEST_DELETE_USER_DATA = "delete_user_data"
DSAR_REQUEST_DELETE_USER_ACCOUNT = "delete_user_account"

DSAR_STATUS_PENDING = "pending"
DSAR_STATUS_FULFILLED = "fulfilled"
DSAR_STATUS_FAILED = "failed"

# We legally need to purge the DSAR logs at least every 12 months.
DSAR_RETENTION_DAYS = 365 