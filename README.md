# SensCritique WeekReal Database 🎬
<p align="center">
  <img src="res/sc.jpg" width="200">
</p>

## Table of Contents  
- [Overview](#overview)
- [Key Features](#key-features)
- [Important Note](#important-note)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Usage](#usage)
- [Reporting and visualization](#reporting-and-visualization)

## Overview
SensCritique WeeklyMovies is a Python ETL (Selenium + TEI) that retrieves weekly movie releases from [senscritique.com](https://www.senscritique.com/), collects reviews, vectorizes texts via [TEI](https://github.com/huggingface/text-embeddings-inference), and loads everything into Postgres + [pgvector](https://github.com/pgvector/pgvector). An optional HF model (if `HF_TOKEN` is provided) classifies sentiments.

<p align="left">
  <img src="res/Pipeline.png" width="600">
</p>

## Key Features
- Weekly scraping of SensCritique movies and reviews (Selenium Remote).
- Embeddings via TEI and vector storage (pgvector).
- Sentiment via HF model (if token available), otherwise explicit `None`.
- Idempotence: `insert_review` ignores URLs already present.
- Makefile scripts to run, migrate, and reset.

## Important Note
- SensCritique HTML changes often: scraping may require updating selectors.
- The HF service is optional: without `HF_TOKEN`, sentiment remains `None`.
- The `pg_data` folder on the host keeps data even after `docker compose down`; delete it to start from scratch.

## Technology Stack
<img src="res/hf.png" width="50"> <img src="res/pg.png" width="50"><img src="res/dock.jpg" width="50"><img src="res/sel.png" width="50"><img src="res/pbi.png" height="50">


- **Text Embedding Inference (TEI)**: For processing and embedding review texts.
- **PGVector**: A vector database for efficient data storage and retrieval.
- **Docker**: For containerizing the ETL process.
- **Selenium**: For web scraping and data extraction.
- **PowerBI**: For reporting.

## Repository Structure
| Path            | Description |
|-----------------|-------------|
| `flow.py`       | Main ETL orchestrator. |
| `src/extract.py`| Movie + review scraping (Selenium). |
| `src/transform.py` | TEI embeddings + HF sentiment. |
| `src/load.py`   | DB connection, upserts, inserts. |
| `sql/schema.sql`| Postgres/pgvector schema. |
| `docker-compose.yml` | Postgres/pgvector, TEI, Selenium, PgAdmin, ETL services. |
| `Makefile`      | Shortcuts: `up`, `down`, `flow`, `migrate`, `reset`, `reset-db`. |
| `reporting/`    | Reporting resources. |

## Usage
1. Start infra: `docker compose up -d`
2. Apply schema: `make migrate`
3. Reset data (optional): `make reset` (drop/recreate schema) or `make reset-db` (TRUNCATE). To start fresh, delete `pg_data`.
4. Run pipeline: `make flow` (reads `WEEK_URL` from `.env` for the target week).

PgAdmin: http://localhost:8081 (admin@admin.com / admin). DB connection: host `postgres`, port `5432`, user/pass `etl`, db `movies`.

Without `HF_TOKEN`, sentiment stays `None` (no heuristic fallback).

# 🎬
