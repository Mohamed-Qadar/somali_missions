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

RUN python manage.py compilemessages \
    && python manage.py collectstatic --noinput

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "somali_missions.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
