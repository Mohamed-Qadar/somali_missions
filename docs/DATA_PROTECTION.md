# Data Protection & Retention

How the Somali Missions platform handles citizen data. This is an engineering description of what the code does; a formal legal/privacy review by the Ministry is still required before launch (see "Requires operational sign-off").

## What data is collected

| Data | When | Notes |
|---|---|---|
| Complaint content (subject, message, category, rating) | Complaint submission | Required |
| Name / email / phone | Complaint (optional), appointment, registration | **Omitted for anonymous complaints** |
| Evidence files | Complaint submission | Type/size validated server-side |
| Appointment + queue details | Booking / walk-in | Name optional for the queue |
| Account (username, email, hashed password, role, mission) | Registration / staff invitation | Passwords hashed by Django (PBKDF2) |
| Audit log (action, IP address, user-agent, timestamp) | Logins, exports, staff actions | For accountability |

## Anonymity

When a complaint is submitted anonymously, the submitter's name, email, and phone are **cleared on save** (see `Complaint.save()`) — they are not stored, not merely hidden in the UI. The public transparency portal only ever shows aggregate statistics and anonymized resolution outcomes; it never renders complainant identity.

## Access control

Citizen data is visible only to: the submitting citizen (via their tracking code / account), staff of the specific mission the complaint/appointment belongs to, and Ministry reviewers/administrators. Enforcement goes through one shared permission layer used by both the web UI and the REST API (see [ARCHITECTURE.md](ARCHITECTURE.md)); cross-mission access is blocked and covered by tests.

## Retention

The platform does not yet enforce automatic data retention/erasure periods — records persist until deleted. Before launch the Ministry should define, and this project should then implement (e.g. as a scheduled Celery job):

- how long resolved/closed complaints and their evidence files are kept;
- how long audit logs are kept;
- a citizen data-erasure / access-request process (to satisfy applicable data-protection law).

The `AuditLog`, backup (`backup_db`), and Celery-Beat scheduling machinery needed to implement retention already exist.

## Transport & storage security

See [../SECURITY.md](../SECURITY.md): HTTPS/HSTS (once TLS is live), hashed passwords, CSRF, validated uploads, and a strict CSP. Uploaded files are stored under `MEDIA_ROOT`; in production this should be a volume with appropriate filesystem permissions (and ideally object storage with private ACLs).

## Requires operational sign-off

- Legal review against the applicable Somali data-protection framework.
- A published privacy notice (the app has a Privacy page; its content should be reviewed by counsel).
- Defined retention periods and a data-subject request process (per above).
