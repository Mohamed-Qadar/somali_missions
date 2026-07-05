# Somali Missions — Complaints & Citizen Protection Platform

Official Django platform for the Somali Ministry of Foreign Affairs: citizens abroad find their nearest mission, submit and track complaints, book appointments, join a walk-in queue, get instant answers from a rule-based assistant, and connect with verified student/community groups. Embassy staff and Ministry users get scoped dashboards, analytics, and a REST API for future mobile clients.

## Requirements

- Python 3.11+
- pip
- Docker + Docker Compose, for a production-like deployment (optional for local dev)

## Quick start (local development, SQLite)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
copy .env.example .env         # Windows — edit SECRET_KEY
# cp .env.example .env

python manage.py migrate
python manage.py seed_missions
python manage.py seed_assistant_topics
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

For a production-style deployment with Postgres, Redis, Celery, and nginx, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Environment variables (`.env`)

See `.env.example` for local dev and `.env.production.example` for the full list used in production (email, Sentry, CORS, Celery, etc). Core variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Optional PostgreSQL URL, e.g. `postgres://user:pass@localhost:5432/dbname` |
| `SECURE_SSL_ENABLED` | Set `True` only once HTTPS is actually terminating in front of the app - enables HSTS/SSL redirect |

## Seed data

```bash
python manage.py seed_missions          # 30 missions worldwide + services + sample complaints
python manage.py seed_assistant_topics  # 12 topics for the Smart Citizen Assistant
python manage.py cleanup_missions       # idempotent - only needed if re-seeding onto old/dirty data
```

Demo accounts created by `seed_missions`:

| User | Password | Lands on |
|------|----------|----------|
| `staff_london` | `staffpass123` | `/dashboard/embassy/` (Embassy Officer, London mission) |
| `ministry_admin` | `adminpass123` | `/dashboard/admin/` (Ministry Administrator, all missions) |

Change or remove these before a real production launch - see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Roles

| Role (`UserProfile.Role`) | Scope |
|---|---|
| `CITIZEN` | Submit/track complaints, book appointments, message verified community groups |
| `EMBASSY_OFFICER` | Cases assigned to them at their own mission |
| `EMBASSY_MANAGER` | All cases + staff assignment at their own mission |
| `MINISTRY_REVIEWER` | National oversight, escalations, analytics (read/act, no user admin) |
| `MINISTRY_ADMIN` | Everything above + user/embassy management |
| `COMMUNITY_REP` | Reserved for community organizations (records managed via Django admin today; no self-service portal yet) |
| Super Admin | A Django superuser (`createsuperuser`) — bypasses role checks and owns `/admin/` |

Roles are the single source of truth: Django Groups and mission staff lists are auto-projected from `UserProfile.role` by a signal (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

## Main features

- Mission directory with country/type/rating filters and a map
- Complaint submission with tracking code, anonymity, CAPTCHA, rate limiting; public track page with optional official response
- **Emergency reporting**: prominent emergency button, typed crisis categories (medical, detention, human trafficking, lost passport, domestic violence, …) stored on the case, server-side validated intake, automatic CRITICAL priority, and a pinned red strip on staff dashboards so emergencies are always worked first
- **Appointments**: book a time slot per mission/service, required-documents checklist shown before booking, QR-coded confirmation, no-double-booking (auto-waitlist), staff approve/reject/reschedule/cancel, daily/weekly/monthly views, reminders
- **Digital queue**: walk-in ticket numbers, live "now serving" display screen, staff call-next/skip/recall/complete, wait-time analytics
- **Smart Citizen Assistant**: rule-based Q&A over 12 topics (passport, visa, documents, appointments, etc.) with a pluggable architecture for a future AI backend
- **Notifications**: in-app + email (SMS/WhatsApp interfaces ready, no provider wired), unread badge, ministry emergency broadcast
- **REST API** at `/api/v1/` (JWT auth, Swagger docs at `/api/v1/docs/`) for future mobile apps
- Ministry KPI dashboard: complaints by mission/country/category, monthly trends, complaints-per-officer, a country×month heatmap, real appointment/queue wait times, CSV + Excel + PDF export
- Full audit log (login/logout/failed-login with IP+user-agent, complaint/appointment/queue/role-change actions, exports)
- English + Somali language switcher — every extracted string now has a Somali translation (AI-assisted; professional native review recommended before launch)
- `/health/` and `/metrics/` (Prometheus) endpoints; Sentry error tracking (opt-in via `SENTRY_DSN`)

## Tests

```bash
python manage.py test
```

72 tests covering models, views, permissions/IDOR scoping, the appointment/queue no-double-booking guarantees, emergency intake validation and dashboard prioritization, the assistant's matching logic, notification channels, the API, brute-force lockout, permission-sync, and query-count (N+1) regressions.

## Documentation

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Docker/production deployment, backups, scheduled jobs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — app/component overview
- [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md) — data model
- [docs/API.md](docs/API.md) — REST API overview
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) · [CONTRIBUTING.md](CONTRIBUTING.md) — conventions & contribution workflow
- [SECURITY.md](SECURITY.md) · [docs/DATA_PROTECTION.md](docs/DATA_PROTECTION.md) · [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) — governance
- [CHANGELOG.md](CHANGELOG.md) — version history
- [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) · [docs/EMBASSY_STAFF_GUIDE.md](docs/EMBASSY_STAFF_GUIDE.md) · [docs/MINISTRY_GUIDE.md](docs/MINISTRY_GUIDE.md) · [docs/CITIZEN_GUIDE.md](docs/CITIZEN_GUIDE.md)

## Project structure

```
somali_missions/     # Django project settings, celery app, root urls
missions/            # Core app: missions, complaints, communities, admin
appointments/        # Appointment booking
queue_management/    # Walk-in digital queue
assistant/           # Smart Citizen Assistant (rule-based)
notifications/       # In-app/email notification center
api/                 # REST API (DRF, JWT, Swagger)
locale/so/           # Somali translations
docs/                # Deployment + architecture + user guides
manage.py
requirements.txt / requirements-dev.txt
Dockerfile / docker-compose.yml / nginx.conf
```
