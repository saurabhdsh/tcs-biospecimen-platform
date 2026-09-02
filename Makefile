.PHONY: up down logs migrate seed test test-e2e reseed build ps

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.seed

reseed:
	docker compose exec backend python -m app.seed --reset

test:
	docker compose exec backend pytest -q

test-e2e:
	docker compose up -d --build
	cd e2e && npm install && npx playwright install --with-deps chromium && npx playwright test
