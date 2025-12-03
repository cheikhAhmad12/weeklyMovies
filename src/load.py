import os
import psycopg
from psycopg.rows import dict_row


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


def upsert_film(conn, film):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO films (film, url)
            VALUES (%(film)s, %(url)s)
            ON CONFLICT (url) DO UPDATE SET film = EXCLUDED.film
            RETURNING id
        """, film)
        return cur.fetchone()["id"]


def insert_review(conn, film_title, row, enriched, emb):
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
