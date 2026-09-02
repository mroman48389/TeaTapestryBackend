# Session Retention Policy

> Tea Tapestry retains session token records for 90 days after the session
> has expired or been revoked. Session tokens contain metadata such as IP
> address, user agent, refresh token identifiers, and authentication
> timestamps. This information is used exclusively for security auditing,
> detecting suspicious login activity, and supporting refresh‑token rotation
> and reuse‑detection mechanisms.
>
> After the retention period expires, session token records are automatically
> deleted by a scheduled maintenance job. The cleanup logic is implemented in
> 
>    `src/maintenance_services/session_retention_service.py` 
> 
> and executed via the script 
> 
>    `scripts/Maintenance/run_session_cleanup.py`.
>
> This policy ensures data minimization, reduces long‑term exposure of
> authentication metadata, and maintains only the operational history required
> for account security and fraud detection.