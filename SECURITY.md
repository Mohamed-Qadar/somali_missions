# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in the Somali Missions platform, please report it privately — **do not open a public issue**.

- Email: **security@mfa.gov.so** (replace with the real security contact before launch)
- Include: a description, steps to reproduce, affected URL/endpoint, and impact.
- Please give us reasonable time to investigate and remediate before any public disclosure.

We aim to acknowledge reports within **3 working days** and to provide a remediation timeline after triage. (These are intended commitments; confirm the operating team can meet them before publishing.)

## Supported versions

The `main` branch is the supported version. Security fixes are applied there and deployed.

## What the platform already does

Security controls implemented in this codebase (see `docs/ARCHITECTURE.md` and the git history for detail):

- **Authentication & authorization**: role-based access via `UserProfile.role` (single source of truth), enforced through shared helpers on every mission-scoped web view and API endpoint; verified by IDOR tests. JWT for the REST API.
- **Brute-force protection**: `django-axes` locks an account after repeated failed logins; plus IP-based rate limiting on login and complaint/emergency intake.
- **Transport & headers**: HSTS + SSL redirect (behind `SECURE_SSL_ENABLED`), a nonce-based Content-Security-Policy with no `script-src 'unsafe-inline'`, `X-Frame-Options: DENY` / `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, Referrer-Policy, secure/HttpOnly/SameSite cookies.
- **Input & uploads**: CSRF protection on all forms, server-side file-type/size validation on evidence and secure-message attachments, captcha + honeypot on complaint intake.
- **Audit trail**: logins, failed logins, logouts, role changes, exports, and complaint/appointment/queue actions are recorded with IP and user-agent.
- **Anonymity**: anonymous complaints do not retain the submitter's name/email/phone (scrubbed on save, not merely hidden).
- **Tooling**: `bandit` static analysis runs in CI at medium+ severity; `manage.py check --deploy` runs in CI.

## Known limitations requiring external validation

These cannot be established inside the development repository and must be completed operationally before a public government launch:

- Independent third-party penetration test.
- Live TLS certificate + verified HTTPS termination (then set `SECURE_SSL_ENABLED=True`).
- Real SMS/WhatsApp provider credentials (interfaces exist; no provider is wired).
- Load / denial-of-service resilience testing.
- Rotation of the seed demo accounts' publicly-known passwords.
