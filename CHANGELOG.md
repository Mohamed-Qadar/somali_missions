# Changelog

All notable changes to the Somali Missions platform. Newest first.

## [Unreleased] — Community self-service portal + Embassy Events

- **Community self-registration** (`/communities/register/`): organizations create a representative account (COMMUNITY_REP) + their org record in Pending review, with the same email-verification flow as citizens; a verification request lands in the Ministry queue. Reps land on their portal after login.
- **Portal upgrade** (`/communities/admin/`): status banner, full profile editing incl. validated logo/banner uploads (PNG/JPG/WEBP, 2/4 MB), service categories, languages, emergency-support availability, `created_by`/`updated_by` audit fields; announcements/events now show their moderation state; success/error toasts (fixed a context clash that silently disabled Django messages on this page).
- **4-state moderation** (Pending/Approved/Rejected/Archived) for community announcements and events via a shared `ModeratedContent` base (with data migration from the old booleans); Ministry moderation queue at `/ministry/community-moderation/` for verification requests, pending content, and abuse reports — all actions audit-logged.
- **Embassy Events** (`MissionEvent`): 8 consular event types (Passport Day, Mobile Consular Service, Student Orientation, Medical/Legal Support, Community Meeting, Emergency Awareness, Document Guidance) with country/city/venue, organizer, registration link, capacity; staff manage events for their own mission only (`/staff/events/`); public listing at `/events/` with country/city/mission/type filters; mission pages show upcoming events next to verified community partners.
- **Abuse reporting**: public, rate-limited reports against verified profiles and approved events; handled from the moderation queue.
- Somali translations for all 150 new strings; nav gains Consular Events + org registration under Community.
- Tests: 72 → 95.

## [Earlier] — Emergency triage, booking checklist, full Somali coverage

- **Emergency intake**: crisis type (medical, detention, trafficking, lost passport, death case, family emergency, child protection, domestic violence, urgent travel, missing person, conflict zone) is now a validated `Complaint.emergency_type` field instead of being discarded; the whole emergency form is server-side validated (the old view accepted empty messages and an unvalidated category from POST) with inline field errors and preserved input.
- **Emergency prioritization**: embassy dashboards order CRITICAL cases first and pin an "Active Emergency / Critical Cases" strip; case rows, the case workspace, ministry urgent alerts, and the Django admin show the crisis type.
- **Appointments**: the booking page shows the selected service's required-documents checklist before the citizen books.
- **Somali translations**: fixed 532 of 720 `.po` entries that had English copied into `msgstr` (silently masking missing translations) — every extracted string now has a real Somali translation (AI-assisted, professional native review recommended); added entries for all new strings and recompiled `django.mo`.
- **Fixed**: staff dashboards used non-existent Tailwind classes (`text-red-650`/`orange-655`/`blue-650`/`emerald-650`), leaving priority/SLA badges unstyled; navbar crowding at ~1280px (community directories grouped under an accessible dropdown).
- Tests: 64 → 72 (emergency validation/typing, dashboard prioritization, booking checklist).

## [Earlier unreleased] — Government production hardening

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
