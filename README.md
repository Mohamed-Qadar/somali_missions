<div align="center">

# 🇸🇴 Somali Missions — Consular Services & Citizen Protection Platform

**Official digital platform of the Somali Ministry of Foreign Affairs for citizens abroad, embassies, and consulates.**

[![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![DRF](https://img.shields.io/badge/REST%20API-DRF%20%2B%20JWT-red)](docs/API.md)
[![Tests](https://img.shields.io/badge/tests-125%20passing-brightgreen)](#tests)
[![i18n](https://img.shields.io/badge/languages-English%20%7C%20Somali-blue)](#internationalisation)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docs/DEPLOYMENT.md)
[![Accessibility](https://img.shields.io/badge/WCAG%202%20AA-0%20violations-success)](docs/ACCESSIBILITY.md)

[Quick start](#quick-start) · [Features](#features) · [Consular services](#consular-services-online-applications) · [Roles](#roles) · [API](#rest-api) · [Deployment](#deployment) · [Docs](#documentation)

</div>

---

## Overview

Somali citizens living, studying or travelling abroad use this platform to:

- **find** their nearest embassy or consulate and see the services it offers,
- **apply online** for consular services (passport, civil registration, document legalisation, …) and track the application by reference number,
- **submit and track complaints**, including anonymous and **emergency** cases,
- **book appointments** or **join a walk-in queue** with a live "now serving" display,
- **get instant answers** from a rule-based Smart Citizen Assistant,
- **connect** with verified student associations and community organisations.

Embassy staff get mission-scoped dashboards for complaints, consular applications, appointments, queues and events. Ministry users get national oversight, moderation queues, KPI analytics and exports. A versioned **REST API** with JWT auth is ready for future mobile clients.

> **Status:** feature-complete pilot. The code is production-hardened (CSP, brute-force lockout, audit log, WCAG AA) but the [pre-deployment checklist](#pre-deployment-checklist) must be completed before a real domain is pointed at it.

---

## Features

| Area | What it does |
|------|--------------|
| **Mission directory** | 30+ missions worldwide with country/type/rating filters, map, services, opening hours, upcoming events and verified community partners per mission |
| **Consular services** | Online applications for 13 standard consular services, 9-state workflow, document uploads, reference-number tracking, staff review queue, optional link to an appointment ([details](#consular-services-online-applications)) |
| **Complaints** | Guided wizard, tracking code, anonymity option, CAPTCHA + rate limiting, public track page with official response |
| **Emergency reporting** | Prominent emergency button, 11 typed crisis categories (medical, detention, trafficking, lost passport, domestic violence, …), server-side validation, automatic CRITICAL priority, pinned red strip on staff dashboards |
| **Appointments** | Per mission/service time slots, required-documents checklist before booking, QR-coded confirmation, no double-booking (auto-waitlist), no past-slot booking, staff approve/reject/reschedule/cancel, daily/weekly/monthly views, reminders |
| **Digital queue** | Walk-in ticket numbers, live display screen, staff call-next / skip / recall / complete, wait-time analytics |
| **Smart Citizen Assistant** | Rule-based Q&A over 12 topics with a pluggable `AnswerProvider` interface for a future AI backend |
| **Community portal** | Organisations self-register (Pending → Verified / Rejected / Suspended), edit their profile (validated logo/banner uploads, service categories, languages, emergency support), publish announcements and events that go live after Ministry moderation, receive citizen messages; public abuse reporting |
| **Embassy events** | Staff publish consular events and campaigns (Passport Day, mobile consular service, orientations, legal/medical support, awareness) for their own mission; public `/events/` listing with country/city/mission/type filters |
| **Notifications** | In-app + email, unread badge, Ministry emergency broadcast; SMS/WhatsApp interfaces ready (no provider wired) |
| **Ministry analytics** | Complaints by mission/country/category, monthly trends, complaints per officer, country × month heatmap, real appointment/queue wait times, CSV / Excel / PDF export |
| **Security & audit** | Nonce-based CSP, `django-axes` lockout, CORS scoped to the API, HSTS/secure cookies behind TLS, full audit log (logins, failed logins with IP + UA, case/appointment/queue/role actions, exports) |
| **Observability** | `/health/`, Prometheus `/metrics/`, optional Sentry |
| **Internationalisation** | Full English + Somali UI with a language switcher |

---

## Consular services (online applications)

The `consular` app lets a citizen apply online for a service at a chosen mission and follow it to completion, while staff process it from a mission-scoped queue.

**Citizen side**

| URL | Purpose |
|-----|---------|
| `/consular/` | Service landing page grouped into four cards: Passport Services, Civil Registration, Document Services, Other Consular Services |
| `/consular/apply/` | Pick mission + service, enter applicant details, upload supporting documents |
| `/consular/my-applications/` | All of the signed-in citizen's applications |
| `/consular/application/<reference>/` | Tracker with status history, staff message and required-document checklist |

**Staff side** (embassy officers and managers, own mission only)

| URL | Purpose |
|-----|---------|
| `/consular/staff/applications/` | Review queue with status filters |
| `/consular/staff/application/<id>/` | Change status, write a citizen-visible message and internal staff notes, link an appointment |

**Workflow states:** `SUBMITTED → UNDER_REVIEW → DOCS_REQUIRED → APPROVED → APPOINTMENT_REQUIRED → COMPLETED`, plus `REJECTED`, `CANCELLED` and `DRAFT`. Every transition is recorded in `ConsularApplicationStatusHistory`.

**Catalogue:** the 13 standard services (passport renewal, new passport, lost/stolen passport, emergency travel document, birth/marriage/death registration, attestation/legalisation, certification, power of attorney, consular letter, citizenship request, other) are plain `MissionService` rows, so each mission can enable, disable or extend them in the admin. `seed_consular_services` installs the catalogue with processing times and required documents on every mission.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (Tailwind, compiled CSS, nonce-CSP)   ·   Mobile (REST/JWT) │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│  Django 5.1                                                          │
│  missions · consular · appointments · queue_management · assistant   │
│  notifications · api (DRF + SimpleJWT + drf-spectacular)             │
│  UserProfile.role  ──signal──▶  Django Groups + Mission.staff_users  │
└───────┬──────────────────┬──────────────────┬────────────────────────┘
        │                  │                  │
   PostgreSQL          Redis (cache,     Celery worker + beat
   (SQLite in dev)     sessions, broker)  (reminders, backups, digests)
```

- **Roles are the single source of truth.** Permissions, Django Groups and mission staff lists are projected from `UserProfile.role` by a signal; `sync_permissions` reconciles existing data.
- **Mission scoping everywhere.** Staff only see cases, applications, appointments, queues and events of their own mission; Ministry roles see all.
- **No duplicated catalogues.** Consular applications, appointments and the booking checklist all reuse `MissionService` and `RequiredDocument`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md).

---

## Quick start

### Requirements

- Python 3.11+
- Node.js 18+ (only to rebuild the Tailwind CSS)
- Docker + Docker Compose for a production-like stack (optional)

### Local development (SQLite)

```bash
git clone https://github.com/<your-username>/somali_missions.git
cd somali_missions

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

pip install -r requirements.txt
copy .env.example .env           # Windows  — then set SECRET_KEY
# cp .env.example .env           # Linux / macOS

python manage.py migrate
python manage.py seed_missions             # 30 missions + services + sample complaints + demo users
python manage.py seed_consular_services    # standard consular catalogue on every mission
python manage.py seed_assistant_topics     # 12 assistant topics
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

### Rebuild CSS (only after editing templates/Tailwind config)

```bash
npm install
npm run build:css
```

### Demo accounts (created by `seed_missions`)

| Username | Password | Role | Lands on |
|----------|----------|------|----------|
| `staff_london` | `staffpass123` | Embassy Officer (London) | `/dashboard/embassy/` |
| `ministry_admin` | `adminpass123` | Ministry Administrator | `/dashboard/admin/` |

> Remove or re-password these before any public deployment.

---

## Environment variables

Copy `.env.example` (dev) or `.env.production.example` (full production list) to `.env`.

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key — **required** in production |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL URL, e.g. `postgres://user:pass@host:5432/db` (SQLite when unset) |
| `REDIS_URL` | Shared cache / Celery broker |
| `SECURE_SSL_ENABLED` | `True` **only once HTTPS terminates in front of the app** — enables HSTS, SSL redirect, secure cookies |
| `EMAIL_*` | SMTP settings for verification and notification emails |
| `SENTRY_DSN` | Optional error tracking |
| `CORS_ALLOWED_ORIGINS` | Origins allowed to call `/api/v1/` |

---

## Roles

| Role (`UserProfile.Role`) | Scope |
|---|---|
| `CITIZEN` | Submit/track complaints, apply for consular services, book appointments, message verified community groups |
| `EMBASSY_OFFICER` | Cases and consular applications assigned at their own mission; queue, appointments and events of that mission |
| `EMBASSY_MANAGER` | Everything an officer sees, plus all cases and staff assignment at their mission |
| `MINISTRY_REVIEWER` | National oversight, escalations, moderation queue, analytics (no user admin) |
| `MINISTRY_ADMIN` | Everything above plus user and embassy management |
| `COMMUNITY_REP` | Community organisation representative: self-registers at `/communities/register/`, manages profile, announcements and events from `/communities/admin/` |
| Super Admin | Django superuser — bypasses role checks and owns `/admin/` |

---

## REST API

- Base URL: `/api/v1/`
- Auth: JWT (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`)
- Interactive docs: `/api/v1/docs/` (Swagger UI) · schema at `/api/v1/schema/`
- Permissions mirror the web roles: staff endpoints are mission-scoped, citizens only see their own records.

See [docs/API.md](docs/API.md).

---

## Internationalisation

English and Somali are fully covered. Every extracted string in `locale/so/LC_MESSAGES/django.po` has a Somali translation (AI-assisted; a native-speaker review is recommended before launch).

```bash
python manage.py makemessages -l so      # extract new strings
python manage.py compilemessages         # rebuild django.mo
```

---

## Tests

```bash
python manage.py test
```

**125 tests** across all apps: models, views, permission/IDOR scoping (anonymous dashboard sweep, citizen isolation, cross-mission blocks, own-org-only community editing), consular application workflow and staff scoping, appointment no-double-booking and no-past-booking guarantees, emergency intake validation and dashboard prioritisation, community registration/verification/moderation visibility, upload validation, abuse reporting, assistant matching, notification channels, API auth, brute-force lockout, permission sync and query-count (N+1) regressions.

Lint and formatting:

```bash
pip install -r requirements-dev.txt
ruff check .
pre-commit install
```

---

## Deployment

A production stack (Gunicorn, PostgreSQL, Redis, Celery worker + beat, nginx) is defined in `docker-compose.yml`.

```bash
cp .env.production.example .env     # fill in secrets
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Full guide, backups and scheduled jobs: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Pre-deployment checklist

1. **Environment** — strong `SECRET_KEY`, `DEBUG=False`, real `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`; run `python manage.py check --deploy` and clear every warning.
2. **TLS** — set `SECURE_SSL_ENABLED=True` only after HTTPS terminates in front of the app.
3. **Email** — configure real SMTP; registration and verification currently use the console backend.
4. **Demo accounts** — remove or re-password `staff_london` / `ministry_admin`; create real staff via the invitation flow.
5. **Media** — serve `MEDIA_ROOT` from a persistent volume or object storage with private ACLs (citizen evidence, consular documents, org logos live there).
6. **Translations** — native Somali review of `django.po`.
7. **Backups & jobs** — schedule `backup_db` and the Celery beat jobs.
8. **External validation** — penetration test, load test, assistive-technology audit, Ministry legal / data-protection sign-off ([docs/DATA_PROTECTION.md](docs/DATA_PROTECTION.md)).

---

## Documentation

| Document | Audience |
|----------|----------|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Ops — Docker, production, backups, scheduled jobs |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md) | Developers — components and data model |
| [docs/API.md](docs/API.md) | Mobile / integration developers |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) · [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors — conventions and workflow |
| [SECURITY.md](SECURITY.md) · [docs/DATA_PROTECTION.md](docs/DATA_PROTECTION.md) · [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) | Governance |
| [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) · [docs/MINISTRY_GUIDE.md](docs/MINISTRY_GUIDE.md) · [docs/EMBASSY_STAFF_GUIDE.md](docs/EMBASSY_STAFF_GUIDE.md) · [docs/CITIZEN_GUIDE.md](docs/CITIZEN_GUIDE.md) | End users |
| [presentation/](presentation/) | Executive summary, slide deck, speaker notes and screenshots for the Ministry |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Project structure

```
somali_missions/     Django project: settings, Celery app, root URLs
missions/            Core: missions, services, complaints, emergencies, communities, events, dashboards, admin
consular/            Online consular applications (citizen apply/track, staff review queue)
appointments/        Appointment booking, waitlist, QR confirmations, reminders
queue_management/    Walk-in digital queue and live display
assistant/           Smart Citizen Assistant (rule-based, pluggable provider)
notifications/       In-app / email notification centre and broadcasts
api/                 REST API (DRF, JWT, Swagger)
locale/so/           Somali translations
docs/                Deployment, architecture, API and user guides
presentation/        Ministry presentation materials
.github/             CI workflows
Dockerfile · docker-compose.yml · nginx.conf · Makefile · pyproject.toml
```

---

## Contributing & security

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Run `ruff check .` and `python manage.py test` locally.
- Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not open public issues for security problems.

## Licence

No open-source licence has been declared yet. All rights reserved by the project owner; add a `LICENSE` file before any public release.
