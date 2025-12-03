.PHONY: up down logs bash migrate db-status reset seed-dates tei-ok tgi-ok flow
DB_HOST=postgres
DB_PORT=5432
DB_USER=etl
DB_PASS=etl
DB_NAME=movies
psql = PGPASSWORD=$(DB_PASS) psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME) -v ON_ERROR_STOP=1

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f

bash:
	docker compose run --rm etl bash

migrate:
	docker compose exec postgres sh -lc '$(psql) -f /app/sql/schema.sql'

db-status:
	docker compose exec postgres sh -lc '$(psql) -c "\dt"'

reset:
	docker compose exec postgres sh -lc '$(psql) -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
	$(MAKE) migrate

seed-dates:
	@echo "No date seed required for current schema."

# Sanity checks TEI / TGI
tei-ok:
	curl -fsS http://localhost:8080/health && echo " TEI OK"

tgi-ok:
	curl -fsS http://localhost:8082/health && echo " TGI OK"

flow:
	docker compose run --rm etl bash -lc "python -m src.flow"

reset-db:
	PGPASSWORD=etl psql -h localhost -p 5434 -U etl -d movies <<'SQL'
	TRUNCATE reviews RESTART IDENTITY CASCADE;
	TRUNCATE pays RESTART IDENTITY CASCADE;
	TRUNCATE scenaristes RESTART IDENTITY CASCADE;
	TRUNCATE realisateurs RESTART IDENTITY CASCADE;
	TRUNCATE producteurs RESTART IDENTITY CASCADE;
	TRUNCATE genres RESTART IDENTITY CASCADE;
	TRUNCATE films RESTART IDENTITY CASCADE;
	SQL
		@echo "📛 Base vidée."
