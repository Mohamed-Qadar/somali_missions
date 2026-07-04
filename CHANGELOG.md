# Changelog

All notable changes to the Somali Missions platform. Newest first.

## [Unreleased] — Government production hardening

- **Frontend**: replaced the Tailwind CDN with a compiled, purged, minified CSS build (Node/Tailwind CLI; rebuilt in the Docker image and CI).
- **Security**: nonce-based Content-Security-Policy (no `script-src 'unsafe-inline'`); `django-axes` brute-force login lockout; CORS scoped to the API; explicit cookie/HSTS/referrer hardening. Fixed a latent multi-backend `login()` bug in the embassy activation flow.
- **Accessibility**: automated axe-core audit (WCAG 2 A/AA) with all audited pages at zero violations — contrast, form labels, keyboard-focusable scroll regions, skip link, ARIA. See `docs/ACCESSIBILITY.md`.
- **Architecture**: `UserProfile.role` is now the single source of truth for permissions; Django Groups and `Mission.staff_users` are auto-projected via a signal (`sync_permissions` command reconciles existing data).
- **Performance/scalability**: DB `CONN_MAX_AGE` + health checks; optional shared Redis cache across workers; query-count regression tests locking in the N+1 fixes.
- **Fixed**: `ministry_analytics` 500 (lazy-proxy JSON serialization) with a regression test.
- **Docs/tooling**: `SECURITY.md`, `CONTRIBUTING.md`, `docs/ACCESSIBILITY.md`, `docs/DATA_PROTECTION.md`, `.dockerignore`, `Makefile`, `pyproject.toml` (ruff), pre-commit config.

## Phase 6 — New government subsystems

- **Appointments** app: slot booking, no-double-booking (auto-waitlist), QR confirmation, staff approve/reject/reschedule, calendar/waitlist/stats, reminders.
- **Digital queue** app: walk-in ticket numbers, live display screen, call-next/skip/recall, wait-time analytics.
- **Smart Citizen Assistant** app: rule-based Q&A over 12 topics with a pluggable `AnswerProvider` for a future AI backend.
- **Notification Center** app: in-app + email (SMS/WhatsApp interfaces ready), unread badge, ministry emergency broadcast.
- **REST API** (`/api/v1/`): DRF, JWT auth, Swagger, mission-scoped permissions for future mobile clients.
- **Ministry KPI dashboard**: complaints-per-officer, country×month heatmap, real appointment/queue wait times, Excel export.
- **System-wide audit logging**: login/logout/failed-login (with IP + user-agent) plus complaint/appointment/queue/role/export actions.
- **DevOps**: Dockerfile, docker-compose (Postgres/Redis/Celery/nginx), `/health/` + `/metrics/`, Sentry (opt-in), GitHub Actions CI, backup/restore commands.

## Phases 2–3 — Audit & remediation

- Fixed email-verification IDOR (now a signed token), secure-message attachment validation, MEDIA storage config, login/complaint/emergency rate limiting.
- Cleaned duplicate/junk mission records and leftover non-English test data (FK-preserving merge).
- Fixed demo staff/ministry accounts not reaching their dashboards.
- Built the "Before You Travel" page; wired the Django messages framework; fixed a broken staff status-update form; fixed mojibake and nav-label inconsistencies.

## Baseline

Existing Django platform: mission directory, complaint submission with secure tracking codes, public tracking, transparency portal, community/student groups, analysis dashboard, PDF/CSV reports, English + Somali.
