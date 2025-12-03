import os
import psycopg
from psycopg.rows import dict_row
from typing import Iterable

def get_conn(dsn: str | None = None):
    """
    Ouvre une connexion PostgreSQL avec autocommit.
    Si dsn est None, lit DATABASE_URL ou utilise un DSN par défaut.
    """
    if dsn is None:
        dsn = os.getenv("DATABASE_URL") or "dbname=movies user=etl password=etl host=postgres port=5432"
    if dsn.startswith("postgresql+"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(dsn, autocommit=True)

def upsert_film(conn, film: dict):
    """
    Insère ou met à jour un film avec ses métadonnées de base.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO films (film, url, rate, date_sortie, image, bande_originale, groupe, annee, duree)
            VALUES (%(film)s, %(url)s, %(rate)s, %(date_sortie)s, %(image)s, %(bande_originale)s, %(groupe)s, %(annee)s, %(duree)s)
            ON CONFLICT (url) DO UPDATE SET
                film = EXCLUDED.film,
                rate = COALESCE(EXCLUDED.rate, films.rate),
                date_sortie = COALESCE(EXCLUDED.date_sortie, films.date_sortie),
                image = COALESCE(EXCLUDED.image, films.image),
                bande_originale = COALESCE(EXCLUDED.bande_originale, films.bande_originale),
                groupe = COALESCE(EXCLUDED.groupe, films.groupe),
                annee = COALESCE(EXCLUDED.annee, films.annee),
                duree = COALESCE(EXCLUDED.duree, films.duree)
            RETURNING id
        """, film)
        return cur.fetchone()["id"]

def _insert_dim_list(conn, table: str, column: str, film_title: str, values: Iterable[str]):
    """
    Insère en masse des lignes (film, value) dans une table dimension simple.
    """
    vals = [v for v in values if v]
    if not vals:
        return
    with conn.cursor() as cur:
        for v in vals:
            cur.execute(
                f"INSERT INTO {table} (film, {column}) VALUES (%s, %s)",
                (film_title, v)
            )

def insert_genres(conn, film_title: str, genres: Iterable[str]):
    _insert_dim_list(conn, "genres", "genre", film_title, genres)

def insert_producteurs(conn, film_title: str, producteurs: Iterable[str]):
    _insert_dim_list(conn, "producteurs", "producteur", film_title, producteurs)

def insert_realisateurs(conn, film_title: str, realisateurs: Iterable[str]):
    _insert_dim_list(conn, "realisateurs", "realisateur", film_title, realisateurs)

def insert_scenaristes(conn, film_title: str, scenaristes: Iterable[str]):
    _insert_dim_list(conn, "scenaristes", "scenariste", film_title, scenaristes)

def insert_pays(conn, film_title: str, pays: Iterable[str]):
    _insert_dim_list(conn, "pays", "pays", film_title, pays)

def insert_review(conn, film_title: str, row, enriched, emb):
    sentiment = (enriched.get("sentiment") or "").lower()
    is_negative = None
    if "neg" in sentiment:
        is_negative = True
    elif "pos" in sentiment:
        is_negative = False

    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO reviews (film, is_negative, title, likes, comments, content, url, embedding)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (url) DO NOTHING
        """, (
            film_title,
            is_negative,
            row.get("titre") or row.get("title"),
            row.get("likes"),
            row.get("comments"),
            row["texte"],
            row["url"],
            emb
        ))
