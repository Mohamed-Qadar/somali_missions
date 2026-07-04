# Deployment Guide

## Prerequisites

- Docker + Docker Compose (v2) on the host
- A domain name pointed at the host, if you want a real hostname instead of a bare IP
- An SMTP account for outgoing mail (registration/verification/notification emails), or accept console-only email for a first test deployment

This guide has been run against this exact `docker-compose.yml`/`Dockerfile` on this codebase's checks, tests, and `collectstatic` locally. It has **not** been run against a live Docker daemon in the environment this project was developed in (Docker Desktop wasn't running there) - review the compose file once yourself before a real production rollout.

## 1. Configure environment

```bash
cp .env.production.example .env
```

Edit `.env` and set at minimum:
- `SECRET_KEY` - generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `ALLOWED_HOSTS` - your real domain(s)
- `POSTGRES_PASSWORD` - a real password
- Email settings if you want real outgoing mail (otherwise it prints to the container logs)

Leave `SECURE_SSL_ENABLED=False` until HTTPS is actually working end-to-end (see step 4) - turning on HSTS before TLS is live can lock browsers out of the site over plain HTTP.

## 2. Build and start

```bash
docker compose build
docker compose up -d
```

This starts: `db` (Postgres), `redis`, `web` (gunicorn, runs migrations on startup), `celery_worker`, `celery_beat` (for scheduled jobs like appointment reminders), and `nginx` (reverse proxy on port 80, serving `/static/` and `/media/` directly).

## 3. Create the first Ministry admin account

```bash
docker compose exec web python manage.py createsuperuser
```

Then, if you want the same demo/seed data used in development (30 missions, sample complaints, assistant topics):

```bash
docker compose exec web python manage.py seed_missions
docker compose exec web python manage.py seed_assistant_topics
```

Skip this on a real production instance unless you specifically want the demo data as a starting point - it includes placeholder complaint data and the `staff_london` / `ministry_admin` demo accounts with publicly-known passwords (see `README.md`); change or remove those before going live.

## 4. Put TLS in front of it

This repo's `nginx.conf` is HTTP-only on purpose - it doesn't assume you have a certificate yet. Two common options:
- Run `certbot` alongside this nginx container (or on the host) to get a Let's Encrypt certificate, add a `443` server block with the cert paths, and redirect `80` to `443`.
- Put a managed load balancer / CDN (that terminates TLS) in front of this stack instead, and leave nginx on plain HTTP behind it.

Once HTTPS is confirmed working end-to-end, set `SECURE_SSL_ENABLED=True` in `.env` and restart the `web` service - this turns on HSTS and forces SSL redirects at the Django level.

## 5. Verify it's healthy

```bash
curl http://your-domain/health/
```

Expect `{"status": "ok", "checks": {"database": true, "cache": true}}`. This endpoint is meant to be wired into your load balancer's/orchestrator's health check.

`http://your-domain/metrics/` exposes Prometheus-format metrics (mission/complaint counts) if you're running a Prometheus scraper.

## Backups

```bash
docker compose exec web python manage.py backup_db
```

Creates a timestamped `.tar.gz` under `backups/` inside the container (a JSON fixture dump of the database + the media directory). Copy it out with `docker compose cp web:/app/backups ./backups` and store it somewhere off-host (S3, another server, etc.) - a backup that only lives on the same disk as the database doesn't protect against disk failure.

Schedule this daily via `celery_beat` (add a periodic task in `/admin/django_celery_beat/periodictask/` pointing at a task, or via host cron running the command above) or, as a simpler alternative, host-level cron:

```cron
0 3 * * * docker compose exec -T web python manage.py backup_db
```

### Restore

```bash
docker compose exec web python manage.py restore_db /app/backups/backup_20260101_030000.tar.gz
```

This is destructive in the sense that it loads fixture data into whatever database is currently there via Django's `loaddata` - it's meant for restoring onto a **fresh** database (e.g. after `docker compose down -v && docker compose up -d` recreated an empty Postgres volume and re-ran migrations), not for merging into a live database that already has different data. Verified locally: a full backup/restore round-trip into a separate fresh SQLite database reproduced every row (581 objects across 20 models in the test run) with correct data intact.

## Scheduled jobs (Celery Beat)

`celery_beat` is running but has no periodic tasks configured out of the box. To make appointment reminders actually fire daily, add a periodic task via `/admin/django_celery_beat/` pointing at `appointments.tasks.send_appointment_reminders_task`, or run it directly via cron as an alternative:

```cron
0 8 * * * docker compose exec -T web python manage.py send_appointment_reminders
```
