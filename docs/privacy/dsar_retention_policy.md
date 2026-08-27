# DSAR Log Retention Policy

> Tea Tapestry retains DSAR (Data Subject Access Request) logs for 12 months
> from the date of the request. These logs are used only for compliance
> verification, operational auditing, and tracking DSAR workflow status.
>
> After the retention period expires, DSAR logs are automatically deleted by
> a scheduled maintenance job. The cleanup logic is implemented in
> 
>    `src/maintenance_services/dsar_retention_service.py` 
> 
> and executed via the script 
> 
>    `scripts/Maintenance/run_dsar_cleanup.py`.
>
> This policy ensures data minimization and reduces long-term exposure of
> personal data while maintaining the operational history required for
> privacy compliance.