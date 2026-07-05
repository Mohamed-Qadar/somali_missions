# Developer Guide

## Setup

See the main [README.md](../README.md) for install steps. For contributing, also install dev tools:

```bash
pip install -r requirements-dev.txt
python -m ruff check .          # lint
python -m bandit -r . -x ./locale,./staticfiles,./venv -ll   # security scan (medium+ only)
python manage.py test           # 72 tests
```

## Frontend CSS (Tailwind)

Styling is Tailwind, **compiled and purged at build time** - not the runtime CDN (which is not for production and forced `'unsafe-inline'`/an external CDN into the CSP). The compiled `missions/static/missions/app.css` is committed so `runserver`/`collectstatic` work without Node, but after editing any template class or `tailwind.config.js`/`missions/static/missions/src/input.css`, rebuild it:

```bash
npm install          # first time only
npm run build:css    # or: npm run watch:css  (rebuild on change during dev)
```

The Docker image rebuilds the CSS from scratch in a Node stage (see `Dockerfile`), and CI runs `npm run build:css` too, so a stale committed `app.css` can't reach production unnoticed.

**CSP note:** every inline `<script>` in the app's own templates must carry `nonce="{{ request.csp_nonce }}"` - `script-src` does not allow `'unsafe-inline'` (see `missions/middleware.py`). If you add an inline script without the nonce, the browser will silently block it. Prefer `{{ data|json_script:"id" }}` + a nonce'd script that reads it, over interpolating server data directly into script text.

## Conventions

**Mission-scoping**: any new view or API endpoint that touches complaint/appointment/queue data must go through `missions/utils/permissions.py`'s `user_is_ministry_admin`, `user_can_manage_mission`, or `missions_for_user` - don't write a new ad hoc permission check. `UserProfile.role`/`mission` is the source of truth; Groups + `Mission.staff_users` are auto-projected from it by a signal (`sync_user_permissions`), so just set the role and don't touch Groups directly. See [ARCHITECTURE.md](ARCHITECTURE.md).

**Tracking codes / tokens**: use `secrets.choice`/`secrets.token_hex` (see `Complaint.generate_tracking_code`, `Appointment.generate_qr_token`), never `random` - anything that acts as a bearer credential (a citizen looks up their case by it, with no password) must be cryptographically unguessable.

**Audit logging**: call `missions.utils.audit.log_audit_action(user, complaint_or_none, action, details, request=request)` for anything that should show up in `/admin/missions/auditlog/` - pass `request` so IP/user-agent get captured. `complaint` is nullable; pass `None` for account-level events.

**Notifications**: call `notifications.channels.notify(recipient, title, body, category=..., channels=['email'])` rather than sending mail directly - this both creates the in-app notification and logs delivery per channel. Don't call `django.core.mail.send_mail` directly outside of `notifications/channels.py` unless there's a specific reason not to go through `notify()` (e.g. the email verification link, which isn't tied to a `Notification`).

**Translations**: wrap every user-facing string in `{% trans %}`/`{% blocktrans %}` (templates) or `gettext`/`gettext_lazy as _` (Python). Only English and Somali are supported - do not add other languages without a product decision, and never mix languages within a single string/record. After adding new strings, regenerate `locale/so/LC_MESSAGES/django.po` with `django-admin makemessages -l so` and compile with `compilemessages` (requires GNU gettext tools - not installed by default on Windows, see below). Without gettext you can still append the entry to `django.po` by hand and compile with `pip install polib` then `python -c "import polib; polib.pofile('locale/so/LC_MESSAGES/django.po').save_as_mofile('locale/so/LC_MESSAGES/django.mo')"`. Never copy the English text into `msgstr` as filler - an empty `msgstr` correctly falls back to English, while an English copy silently hides the missing translation (532 of 720 entries had this problem; all are now genuinely translated, AI-assisted, pending professional native review before launch).

**No half-finished features**: if something can't be fully implemented (e.g. an external provider isn't configured), build the real interface/architecture and make it honestly report that it didn't do the thing (see `notifications/channels.py`'s `SMSChannel`/`WhatsAppChannel` - they return `delivered=False` and log the intent, they don't pretend to send a text).

## Adding a new Django app

Follow the pattern of `appointments`/`queue_management`/`assistant`/`notifications`:
1. `python manage.py startapp <name>`
2. Add to `INSTALLED_APPS` in `somali_missions/settings.py`
3. `models.py` importing from `missions.models` as needed (never the reverse - `missions` is the foundation app and must not import from the newer apps)
4. `views.py` using `missions.utils.permissions` for any scoped access
5. `admin.py`, `urls.py`, wire the urls into `somali_missions/urls.py`
6. Real tests in `tests.py` - see any of the four apps above for the expected depth (not just "does the page return 200", but the actual guarantees: scoping, no-double-booking, etc.)
7. If it needs API exposure, add serializers/viewsets to `api/` rather than building parallel API code inside the new app

## Local dev in a synced folder (OneDrive/Dropbox) — stale server gotcha

If the project lives in a OneDrive/Dropbox-synced folder, Django's `runserver`
auto-reloader (`StatReloader`) can miss file changes because the sync client
interferes with file-modification events. Symptom: you edit a view/URL/template,
the browser still shows old behaviour or a `NoReverseMatch`/500 for something
you already added. **Fix: stop and restart `runserver`** after changes (or move
the project outside the synced folder for development). This only affects the
dev auto-reloader — production runs under gunicorn with no reloader, so it is
not a production concern.

## Gettext tooling on Windows

`compilemessages` needs `msgfmt` (part of GNU gettext), which isn't bundled with Git for Windows. Options: WSL, a standalone gettext installer, or run `compilemessages` in the Docker build (the `Dockerfile` installs `gettext` via apt and compiles translations at build time) if you don't want to install it locally.

## Database

SQLite locally by default; set `DATABASE_URL=postgres://...` to use Postgres (same as production). Both are exercised by the same migrations - don't write raw SQL that only works on one backend. `CONN_MAX_AGE` keeps connections persistent; `REDIS_URL` (when set) switches the cache from per-process memory to a shared Redis so caching/rate-limits work across gunicorn workers.

## Settings & tooling

Configuration is a single env-driven `somali_missions/settings.py` (12-factor style): behaviour differs by environment variable (`DEBUG`, `SECURE_SSL_ENABLED`, `DATABASE_URL`, `REDIS_URL`, `SENTRY_DSN`, `AXES_*`, ...), not by separate per-environment modules. This keeps one file to reason about; local dev needs almost no env vars, production sets them via `.env` (see `.env.production.example`).

Helpers:
- `make` targets wrap the common commands (`make all-checks` runs lint + security + system checks + tests, i.e. what CI runs). On Windows run the underlying commands directly.
- `pyproject.toml` pins the ruff config so local, `pre-commit`, and CI lint identically.
- `.pre-commit-config.yaml` runs ruff + hygiene hooks before each commit (`pip install pre-commit && pre-commit install`).
- `.dockerignore` keeps host-only/secret files (`.env`, `db.sqlite3`, `node_modules`, `.git`) out of the image.
