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
SensCritique WeeklyMovies est un ETL Python (Selenium + TEI) qui récupère les sorties ciné de la semaine sur [senscritique.com](https://www.senscritique.com/), collecte les critiques, vectorise les textes via [TEI](https://github.com/huggingface/text-embeddings-inference) et charge le tout dans Postgres + [pgvector](https://github.com/pgvector/pgvector). Un modèle HF optionnel (si `HF_TOKEN` est fourni) classe les sentiments.

<p align="left">
  <img src="res/Pipeline.png" width="600">
</p>

## Key Features
- Scraping hebdo des films et critiques SensCritique (Selenium Remote).
- Embeddings via TEI et stockage vectoriel (pgvector).
- Sentiment via modèle HF (si token dispo), sinon `None` explicite.
- Idempotence : `insert_review` ignore les URLs déjà présentes.
- Scripts Makefile pour lancer, migrer, réinitialiser.

## Important Note
- Le HTML SensCritique change souvent : la collecte peut nécessiter d’ajuster les sélecteurs.
- Le service HF est optionnel : sans `HF_TOKEN`, le sentiment reste `None`.
- Le dossier `pg_data` sur l’hôte conserve les données même après `docker compose down`; supprime-le pour repartir de zéro.

## Technology Stack
<img src="res/hf.png" width="50"> <img src="res/pg.png" width="50"><img src="res/dock.jpg" width="50"><img src="res/sel.png" width="50"><img src="res/pbi.png" height="50">


- **Text Embedding Inference (TEI)**: For processing and embedding review texts.
- **PGVector**: A vector database for efficient data storage and retrieval.
- **Docker**: For containerizing the ETL process.
- **Selenium**: For web scraping and data extraction.
- **PwerBI**: For reporting.

## Repository Structure
| Path            | Description |
|-----------------|-------------|
| `flow.py`       | Orchestrateur principal de l’ETL. |
| `src/extract.py`| Scraping films + critiques (Selenium). |
| `src/transform.py` | Embeddings TEI + sentiment HF. |
| `src/load.py`   | Connexion DB, upserts, inserts. |
| `sql/schema.sql`| Schéma Postgres/pgvector. |
| `docker-compose.yml` | Services Postgres/pgvector, TEI, Selenium, PgAdmin, ETL. |
| `Makefile`      | Raccourcis : `up`, `down`, `flow`, `migrate`, `reset`, `reset-db`. |
| `reporting/`    | Ressources de reporting. |

## Usage
1. Lancer l’infra : `docker compose up -d`
2. Appliquer le schéma : `make migrate`
3. Nettoyer la base si besoin : `make reset` (drop/recreate schema) ou `make reset-db` (TRUNCATE). Pour repartir à blanc, supprimer `pg_data`.
4. Exécuter le pipeline : `make flow` (utilise `WEEK_URL` depuis `.env` pour la semaine à scraper).

PgAdmin : http://localhost:8081 (admin@admin.com / admin), connexion Postgres : host `postgres`, port `5432`, user/pass `etl`, db `movies`.

Sans `HF_TOKEN`, le sentiment restera `None` (pas de fallback heuristique).

# 🎬
