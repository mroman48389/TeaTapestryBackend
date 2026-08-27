REQUEST_EXPORT_USER_DATA = "export_user_data"
REQUEST_DELETE_USER_DATA = "delete_user_data"
REQUEST_DELETE_USER_ACCOUNT = "delete_user_account"

STATUS_PENDING = "pending"
STATUS_FULFILLED = "fulfilled"
STATUS_FAILED = "failed"

# We legally need to purge the DSAR logs at least every 12 months.
RETENTION_DAYS = 365 