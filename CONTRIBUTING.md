# Contributing

## Getting started

```bash
pip install -r requirements-dev.txt
npm install
python manage.py migrate
python manage.py seed_missions
python manage.py seed_assistant_topics
python manage.py runserver
```

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for conventions (mission-scoping, token generation, audit logging, notifications, translations, the Tailwind CSS build, adding a new app).

## Before you open a pull request

Run what CI runs:

```bash
make all-checks        # ruff + bandit + manage.py check + tests
# or individually:
python -m ruff check .
python -m bandit -r . -x ./locale,./staticfiles,./venv,./node_modules -ll
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
npm run build:css      # if you changed template classes or the theme
```

Install the pre-commit hooks so lint runs automatically:

```bash
pip install pre-commit && pre-commit install
```

## Expectations

- **Tests**: new behaviour needs tests. Match the depth of the existing suites — assert the real guarantee (permission scoping, no-double-booking, query counts), not just a 200 response.
- **Migrations**: commit the generated migration; `makemigrations --check` must be clean.
- **Accessibility**: new pages must pass an axe-core run (WCAG 2 A/AA) — see [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md).
- **Security**: don't weaken the CSP, permission helpers, or CSRF/rate-limit protections. Bandit must stay clean at medium+.
- **i18n**: wrap user-facing strings in `{% trans %}`/`gettext`. English and Somali only.
- **No fabricated completeness**: if something can't be finished (e.g. an external provider isn't configured), build the real interface and make it honestly report that it didn't act, rather than pretending.

## Commits

Write descriptive commit messages that explain the *why*, not just the *what*. Keep unrelated changes in separate commits.
