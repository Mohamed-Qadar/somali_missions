# ---- Stage 1: build the purged Tailwind CSS ----
# Runs the same `npm run build:css` a developer runs locally, so the image
# never ships stale CSS - it's always compiled from the current templates.
FROM node:22-slim AS css
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY tailwind.config.js ./
COPY missions/static/missions/src ./missions/static/missions/src
COPY missions/templates ./missions/templates
COPY appointments/templates ./appointments/templates
COPY queue_management/templates ./queue_management/templates
COPY assistant/templates ./assistant/templates
COPY notifications/templates ./notifications/templates
RUN npm run build:css

# ---- Stage 2: the Django application ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=somali_missions.settings

WORKDIR /app

# libpq5 is the runtime library psycopg2-binary needs; gettext provides
# msgfmt for compiling translations at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use the freshly-built CSS from the css stage (overwrites any committed copy).
COPY --from=css /app/missions/static/missions/app.css ./missions/static/missions/app.css

RUN python manage.py compilemessages \
    && python manage.py collectstatic --noinput

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "somali_missions.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
