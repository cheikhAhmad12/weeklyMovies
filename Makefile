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
	docker compose exec postgres sh -lc '$(psql) -f /app/sql/000_init_extensions.sql'
	docker compose exec postgres sh -lc '$(psql) -f /app/sql/010_dim_tables.sql'
	docker compose exec postgres sh -lc '$(psql) -f /app/sql/020_fact_tables.sql'

db-status:
	docker compose exec postgres sh -lc '$(psql) -c "\dt"'

reset:
	docker compose exec postgres sh -lc '$(psql) -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
	$(MAKE) migrate

seed-dates:
	docker compose exec postgres sh -lc '$(psql) -f /app/sql/populate_date.sql'

# Sanity checks TEI / TGI
tei-ok:
	curl -fsS http://localhost:8080/health && echo " TEI OK"

tgi-ok:
	curl -fsS http://localhost:8082/health && echo " TGI OK"

flow:
	docker compose run --rm etl bash -lc "python -m src.flows.weekly_pipeline"

reset-db:
	PGPASSWORD=etl psql -h localhost -p 5434 -U etl -d movies <<'SQL'
	TRUNCATE fact_critique RESTART IDENTITY CASCADE;
	TRUNCATE dim_film RESTART IDENTITY CASCADE;
	TRUNCATE dim_source RESTART IDENTITY CASCADE;
	SQL
		@echo "📛 Base vidée (hors dim_date)."

