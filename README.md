# Somali Missions — Complaint & Evaluation Platform

Django web application for collecting and analyzing citizen feedback on Somali embassies and consulates worldwide.

## Requirements

- Python 3.11+
- pip

## Quick start

```bash
cd somali_missions
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
copy .env.example .env         # Windows — edit SECRET_KEY
# cp .env.example .env

python manage.py migrate
python manage.py seed_missions
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Environment variables (`.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Optional PostgreSQL URL, e.g. `postgres://user:pass@localhost:5432/dbname` |

When `DEBUG=False`, these security settings are enabled automatically:

- `SECURE_BROWSER_XSS_FILTER`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `X_FRAME_OPTIONS = DENY`

Use HTTPS in production so secure cookies work correctly.

## Seed data

`python manage.py seed_missions` creates 16 missions, sample complaints, and demo users:

| User | Password | Role |
|------|----------|------|
| `staff_london` | `staffpass123` | Mission staff (London embassy) |
| `ministry_admin` | `adminpass123` | Ministry admin group |

## Main features

- Mission search with country / type / rating filters and map
- Complaint submission with tracking code, anonymity, CAPTCHA, rate limiting
- Public track page (`/track/`) with optional official response
- Analysis dashboard with Chart.js and period filters
- PDF reports (3 types) and CSV export (login required)
- Staff panel for status updates and public responses
- English + Somali language switcher
- Contact form, FAQ, privacy policy

## Tests

```bash
python manage.py test
```

## Project structure

```
somali_missions/     # Django project settings
missions/            # Main app (models, views, templates)
locale/so/           # Somali translations
manage.py
requirements.txt
```
