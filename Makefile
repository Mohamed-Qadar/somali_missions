# Common developer/CI commands. On Windows, run the underlying commands
# directly (or use `make` via Git Bash / WSL).

.PHONY: install css watch run migrate seed test lint security check deploy-check all-checks docker-build

install:          ## Install Python + Node dependencies
	pip install -r requirements-dev.txt
	npm install

css:              ## Build the purged, minified Tailwind CSS
	npm run build:css

watch:            ## Rebuild CSS on change (dev)
	npm run watch:css

run:              ## Run the dev server
	python manage.py runserver

migrate:          ## Apply database migrations
	python manage.py migrate

seed:             ## Load demo data (missions + assistant topics)
	python manage.py seed_missions
	python manage.py seed_assistant_topics

test:             ## Run the test suite
	python manage.py test

lint:             ## Lint with ruff
	python -m ruff check .

security:         ## Security scan with bandit (medium+ severity)
	python -m bandit -r . -x ./locale,./staticfiles,./venv,./node_modules -ll

check:            ## Django system checks
	python manage.py check

deploy-check:     ## Django production-readiness checks
	python manage.py check --deploy

all-checks: lint security check test  ## Run everything CI runs

docker-build:     ## Build the production Docker image
	docker build -t somali-missions:local .
