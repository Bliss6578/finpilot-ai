# FinPilot production runbook

## Required controls

- Use managed PostgreSQL with daily provider snapshots and point-in-time recovery enabled.
- Store `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`, Razorpay credentials and email credentials only in the hosting secret store.
- Run `alembic upgrade head` during every backend release before accepting traffic.
- Schedule `backend/scripts/backup_postgres.sh` daily to encrypted object storage. Keep 14 daily and 3 monthly copies.
- Test `backend/scripts/restore_postgres.sh` against a disposable database every month.
- Alert on readiness failure, HTTP 5xx rate, webhook failures, sync failures, database capacity and backup age.
- Rotate the encryption key and Razorpay webhook secrets through a documented dual-key migration; never replace a key without re-encrypting stored credentials.

## Recovery objectives

- Target RPO: 24 hours with daily dumps; use provider PITR for a lower RPO.
- Target RTO: 2 hours. Restore PostgreSQL, run migrations, verify `/api/readiness`, then enable webhook delivery.
- Re-run Razorpay synchronization after recovery to reconcile the restored database with provider records.

## Security verification

Run backend tests, frontend type-check/build, dependency audit, tenant-isolation tests, and browser regression tests before release. Review CORS, cookie flags, rate limits, security headers, logs for secret leakage, and database backup age.
