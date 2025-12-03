import os
import requests
import psycopg
from psycopg.rows import dict_row

# -------------------------
# 1) Fonctions DB
# -------------------------

def get_conn(dsn: str | None = None):
    """
    Ouvre une connexion à PostgreSQL.
    - Si dsn est None, on prend DATABASE_URL ou un DSN par défaut.
    - Si DATABASE_URL est un URL SQLAlchemy (postgresql+psycopg://),
      on le convertit en URL psycopg standard (postgresql://).
    """
    if dsn is None:
        dsn = os.getenv("DATABASE_URL") or "dbname=movies user=etl password=etl host=postgres port=5432"

    # Normalisation: transformer l'URL SQLAlchemy en URL psycopg valide
    if dsn.startswith("postgresql+"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)

    return psycopg.connect(dsn, autocommit=True)


def upsert_film(conn, film: dict) -> int:
    """
    Crée ou met à jour un film dans la table films
    et renvoie l'id.
    film = {"film": ..., "url": ...}
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO films (film, url)
            VALUES (%(film)s, %(url)s)
            ON CONFLICT (url)
            DO UPDATE SET film = EXCLUDED.film
            RETURNING id
            """,
            film,
        )
        row = cur.fetchone()
        return row["id"]


def insert_review(conn, film_title: str, row, enriched, emb) -> bool:
    """
    Insert une critique dans reviews. Retourne True si insérée, False si déjà présente (conflit URL).
    """
    sentiment = (enriched.get("sentiment") or "").lower()
    is_negative = None
    if "neg" in sentiment:
        is_negative = True
    elif "pos" in sentiment:
        is_negative = False

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO reviews (film, is_negative, title, likes, comments, content, url, embedding)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (url) DO NOTHING
            """,
            (
                film_title,
                is_negative,
                row.get("titre") or row.get("title"),
                row.get("likes"),
                row.get("comments"),
                row["texte"],
                row["url"],
                emb,
            ),
        )
        return cur.rowcount == 1


# -------------------------
# 2) Fonctions d'enrichissement (TGI + TEI)
# -------------------------

def enrich_with_llm_and_embedding(texte: str):
    """
    Appelle TGI pour obtenir un résumé / sentiment / thèmes,
    et TEI pour obtenir l'embedding du texte.
    """
    TGI = os.getenv("TGI_URL", "http://tgi:80")
    TEI = os.getenv("TEI_URL", "http://tei:80")

    # Appel TGI (génération)
    resp = requests.post(
        f"{TGI}/generate",
        json={
            "inputs": (
                "1) Résume la critique en 1 phrase.\n"
                "2) Donne le sentiment (positif / neutre / négatif).\n"
                "3) Donne une liste de 3 à 5 thèmes (mots-clés).\n\n"
                f"Critique : {texte}"
            ),
            "parameters": {"max_new_tokens": 120, "temperature": 0.2},
        },
        timeout=200,
    )
    data = resp.json()
    gen_text = data.get("generated_text", "")

    # Pour l'instant : on stocke le texte généré tel quel,
    # et on conserve un label simple pour l'insertion.
    enriched = {
        "resume": gen_text,
        "sentiment": gen_text.lower(),  # heuristique simple, détectée plus tard
        "themes": [],
    }

    # Appel TEI (embedding)
    resp_emb = requests.post(
        f"{TEI}/embed",
        json={"inputs": [texte]},
        timeout=60,
    )
    emb = resp_emb.json()[0]  # vecteur 384

    return enriched, emb

# -------------------------
# 3) Fausse "scrape" (données factices)
# -------------------------

def fake_scrape_reviews():
    """
    Simule le résultat d'un scraping SensCritique.
    Retourne une liste de dicts au format attendu par insert_review.
    Plus tard tu remplaceras ça par un vrai scraping Selenium.
    """
    critiques = []

    # Critique 1
    texte1 = "Film très touchant, avec une réalisation solide et des acteurs convaincants."
    url1 = "https://www.senscritique.com/film/film_test_1/critique/1"
    critiques.append({
        "titre": "Film test 1",
        "film_url": "https://www.senscritique.com/film/film_test_1",
        "auteur": "UserA",
        "note": 8.0,
        "texte": texte1,
        "url": url1,
    })

    # Critique 2
    texte2 = "Comédie correcte, quelques bonnes blagues mais un scénario assez prévisible."
    url2 = "https://www.senscritique.com/film/film_test_2/critique/2"
    critiques.append({
        "titre": "Film test 2",
        "film_url": "https://www.senscritique.com/film/film_test_2",
        "auteur": "UserB",
        "note": 6.5,
        "texte": texte2,
        "url": url2,
    })

    texte3 = "Horreur movie, J ai vraiment eu tres peur."
    url3 = "https://www.senscritique.com/film/film_test_3/critique/3"
    critiques.append({
        "titre": "Film test 3",
        "film_url": "https://www.senscritique.com/film/film_test_3",
        "auteur": "UserB",
        "note": 6.5,
        "texte": texte3,
        "url": url3,
    })
    # Tu peux en ajouter d'autres si tu veux
    return critiques

# -------------------------
# 4) Orchestrateur principal
# -------------------------

def run_weekly(limit: int = 10):
    """
    Pipeline principal :
      1) Récupère des critiques (fake pour l'instant)
      2) Enrichit via TGI + TEI
      3) Upsert films
      4) Insert reviews (vector)
    """
    print("🚀 Démarrage du pipeline weekly...")

    # 1) Connexion DB
    conn = get_conn()
    print("✅ Connexion DB OK")

    # 2) Récupération des critiques (fake pour l'instant)
    all_reviews = fake_scrape_reviews()
    reviews = all_reviews[:limit] if limit else all_reviews

    print(f"📄 Nombre de critiques à traiter: {len(reviews)}")

    # 3) Boucle principale
    inserted = 0
    skipped = 0
    for row in reviews:
        try:
            print(f"\n▶ Traitement critique URL={row['url']}")
            # 3.1 Upsert film
            film = {
                "film": row["titre"],
                "url": row["film_url"],
            }
            film_id = upsert_film(conn, film)
            print(f"   🎬 film_id={film_id} ({film['film']})")

            # 3.2 Enrichissement LLM + embedding
            enriched, emb = enrich_with_llm_and_embedding(row["texte"])
            print("   🧠 enrichissement OK")

            # 3.3 Insertion review
            ok = insert_review(conn, film["film"], row, enriched, emb)
            if not ok:
                print("   ⚠️ Critique déjà en base (url).")
                skipped += 1
            else:
                print("   ✅ Critique insérée.")
                inserted += 1
        except Exception as e:
            print(f"   ❌ ERREUR sur {row['url']}: {e}")

    conn.close()
    print(f"\n📊 Résumé: {inserted} insertions, {skipped} ignorées.")
    print("✅ Pipeline terminé.")


def count_facts(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM reviews;")
        return cur.fetchone()[0]


if __name__ == "__main__":
    # Quand tu fais "python -m src.flows.weekly_pipeline" dans le conteneur,
    # c'est cette fonction qui est appelée.
    run_weekly(limit=10)
