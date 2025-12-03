import psycopg
from psycopg.rows import dict_row

def get_conn(dsn:str):
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
