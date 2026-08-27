# Tea Tapestry Privacy and Compliance Checklist

This checklist tracks all engineering requirements related to DSAR (Data Subject
Access Request) compliance, user data deletion, and privacy obligations.

## DSAR Features
- [x] User data export endpoint
- [x] User account deletion endpoint
- [x] User data deletion endpoint
- [x] DSAR log model for tracking requests
- [x] DSAR log retention service (12 months)
- [x] Automated DSAR log cleanup job (local Windows scheduler)
- [ ] Automated DSAR log cleanup job for Fly.io (staging, production)
- [x] Fresh-login requirement for sensitive DSAR actions
- [x] Downloadable JSON file for data export (optional but user-friendly)
- [ ] Audit logging for DSAR exports and deletions

