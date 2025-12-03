# SensCritique WeeklyMovies – Branch Guide

This branch reorganizes the ETL around a simple weekly pipeline, a lean schema, and explicit TEI/LLM enrichment. It scrapes (or mocks) SensCritique reviews, enriches them, and stores them in a PGVector-enabled Postgres instance ready for analytics.

## Core flow
- **Orchestrator**: `src/flows/weekly_pipeline.py` is the main entrypoint (`python -m src.flows.weekly_pipeline`). It connects to Postgres, pulls reviews (currently a fake scrape stub), enriches each review with LLM + embeddings, upserts films, and inserts critiques.
- **Scraping**: `src/extract/senscritique.py` holds Selenium/BS4 helpers (`weekly_releases`, `film_reviews`, `make_driver`). You can replace the fake data in the flow with these when the selectors are finalized. Selenium runs against the `selenium` service URL in env (`SELENIUM_REMOTE_URL`).
- **Enrichment**: 
  - `src/transform/llm.py` calls a TGI endpoint to summarize/tag sentiment/themes (JSON).
  - `src/transform/embeddings.py` calls TEI to embed review text (vector length depends on the model; default MiniLM 384 dims).
- **Database I/O**: 
  - `src/load/db.py` exposes helpers to open a psycopg connection, upsert films (`films` table), and insert reviews (`reviews` table with embeddings).
  - `src/config.py` centralizes env-driven settings (`DATABASE_URL`, `TEI_URL`, `TGI_URL`, `SELENIUM_REMOTE_URL`).

## Data model
- SQL DDL is consolidated in `sql/schema.sql`: it creates the vector extension and the core tables (`films`, `genres`, `producteurs`, `realisateurs`, `scenaristes`, `pays`, `reviews` with a `vector(384)` embedding column).
- Reviews store raw text plus the vector; film metadata tables are ready for richer scrape output when you wire the real scraper.

## Runtime stack
- `docker-compose.yml` brings up Postgres (PGVector), pgAdmin, TEI (text-embeddings-inference), Selenium (standalone Chromium), Prefect (optional UI), and the `etl` container (built from `Dockerfile`).
- `requirements.txt` pins the Python deps (psycopg3, Prefect 3, Selenium, BS4, requests, pandas, pydantic, alembic).
- `Dockerfile` builds a slim Python image, installs deps, copies the repo, and runs the weekly pipeline module by default.

## How to run
1) `docker-compose up -d` (wait for Postgres/TEI healthchecks).  
2) Initialize schema in Postgres using `sql/schema.sql` (e.g., mount on start or `psql -f sql/schema.sql`).  
3) Ensure env vars for the ETL container: `DATABASE_URL` (psycopg DSN), `TEI_URL`, optional `TGI_URL`, and `SELENIUM_REMOTE_URL`. Defaults in compose point to local services.  
4) Run the pipeline inside the container: `docker compose exec etl python -m src.flows.weekly_pipeline`.  
5) Swap the fake scrape in `run_weekly` with `src.extract.senscritique` helpers once your selectors are validated.  

## Files of interest
- Pipelines: `src/flows/weekly_pipeline.py`, `src/flows/fake/weekly_pipeline1.py`, `src/flows/fake/weekly_pipeline2.py` (experiments).
- Scraping: `src/extract/senscritique.py`.
- Enrichment: `src/transform/llm.py`, `src/transform/embeddings.py`.
- DB layer: `src/load/db.py`; schema SQL in `sql/`.
- Notebooks/research: `model_study/model_study.ipynb`, `model_study/report.pdf`.
