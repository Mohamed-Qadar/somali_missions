# Developer Guide

## Setup

See the main [README.md](../README.md) for install steps. For contributing, also install dev tools:

```bash
pip install -r requirements-dev.txt
python -m ruff check .          # lint
python -m bandit -r . -x ./locale,./staticfiles,./venv -ll   # security scan (medium+ only)
python manage.py test           # 53 tests
```

## Conventions

**Mission-scoping**: any new view or API endpoint that touches complaint/appointment/queue data must go through `missions/utils/permissions.py`'s `user_is_ministry_admin`, `user_can_manage_mission`, or `missions_for_user` - don't write a new ad hoc permission check. See [ARCHITECTURE.md](ARCHITECTURE.md) for why there are two provisioning paths these functions reconcile.

**Tracking codes / tokens**: use `secrets.choice`/`secrets.token_hex` (see `Complaint.generate_tracking_code`, `Appointment.generate_qr_token`), never `random` - anything that acts as a bearer credential (a citizen looks up their case by it, with no password) must be cryptographically unguessable.

**Audit logging**: call `missions.utils.audit.log_audit_action(user, complaint_or_none, action, details, request=request)` for anything that should show up in `/admin/missions/auditlog/` - pass `request` so IP/user-agent get captured. `complaint` is nullable; pass `None` for account-level events.

**Notifications**: call `notifications.channels.notify(recipient, title, body, category=..., channels=['email'])` rather than sending mail directly - this both creates the in-app notification and logs delivery per channel. Don't call `django.core.mail.send_mail` directly outside of `notifications/channels.py` unless there's a specific reason not to go through `notify()` (e.g. the email verification link, which isn't tied to a `Notification`).

**Translations**: wrap every user-facing string in `{% trans %}`/`{% blocktrans %}` (templates) or `gettext`/`gettext_lazy as _` (Python). Only English and Somali are supported - do not add other languages without a product decision, and never mix languages within a single string/record. After adding new strings, regenerate `locale/so/LC_MESSAGES/django.po` with `django-admin makemessages -l so` and compile with `compilemessages` (requires GNU gettext tools - not installed by default on Windows, see below).

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

## Gettext tooling on Windows

`compilemessages` needs `msgfmt` (part of GNU gettext), which isn't bundled with Git for Windows. Options: WSL, a standalone gettext installer, or run `compilemessages` in the Docker build (the `Dockerfile` installs `gettext` via apt and compiles translations at build time) if you don't want to install it locally.

## Database

SQLite locally by default; set `DATABASE_URL=postgres://...` to use Postgres (same as production). Both are exercised by the same migrations - don't write raw SQL that only works on one backend.
