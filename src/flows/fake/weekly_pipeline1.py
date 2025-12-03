import os
import hashlib
import requests
import psycopg
from psycopg.rows import dict_row

# -------------------------
# 1) Fonctions DB existantes
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
        # ex: postgresql+psycopg://etl:etl@postgres:5432/movies
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)

    return psycopg.connect(dsn, autocommit=True)



def upsert_film(conn, film: dict) -> int:
    """
    Crée ou met à jour un film dans dim_film
    et renvoie film_id.
    film = {"titre": ..., "url": ...}
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO dim_film (titre, senscritique_url)
            VALUES (%(titre)s, %(url)s)
            ON CONFLICT (senscritique_url)
            DO UPDATE SET titre = EXCLUDED.titre
            RETURNING film_id
            """,
            film,
        )
        row = cur.fetchone()
        return row["film_id"]


def ensure_source(conn, name: str = "SensCritique") -> int:
    """
    S'assure que la source existe dans dim_source
    et renvoie source_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_source(nom) VALUES (%s) ON CONFLICT (nom) DO NOTHING;",
            (name,),
        )
        cur.execute("SELECT source_id FROM dim_source WHERE nom=%s;", (name,))
        return cur.fetchone()[0]


def insert_review(conn, film_id, source_id, row, enriched, emb):
    """
    Insère une critique dans fact_critique, en évitant les doublons (hash_critique).
    row doit contenir au minimum:
      - auteur
      - note
      - texte
      - url
      - hash_critique
    enriched doit contenir:
      - resume
      - sentiment
      - themes (list)
    emb = vector (liste de float de taille 384)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_critique (
                film_id, source_id, auteur, date_publication, note_numeric,
                texte, resume_llm, sentiment_label, themes, embedding, url, hash_critique
            )
            VALUES (%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (hash_critique) DO NOTHING
            """,
            (
                film_id,
                source_id,
                row.get("auteur"),
                row.get("note"),
                row["texte"],
                enriched.get("resume"),
                enriched.get("sentiment"),
                enriched.get("themes"),
                emb,
                row["url"],
                row["hash_critique"],
            ),
        )

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
        timeout=60,
    )
    data = resp.json()
    gen_text = data.get("generated_text", "")

    # Pour l'instant : on ne parse pas finement, on stocke tout dans resume.
    enriched = {
        "resume": gen_text,
        "sentiment": "inconnu",     # TODO: parser gen_text pour extraire le label
        "themes": ["a_classer"],    # TODO: parser gen_text pour extraire les thèmes
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

    def make_hash(texte, url):
        return hashlib.md5(f"{texte}|{url}".encode("utf-8")).hexdigest()

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
        "hash_critique": make_hash(texte1, url1),
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
        "hash_critique": make_hash(texte2, url2),
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
      4) Insert fact_critique
    """
    print("🚀 Démarrage du pipeline weekly...")

    # 1) Connexion DB
    conn = get_conn()
    print("✅ Connexion DB OK")

    # 2) Source
    source_id = ensure_source(conn, "SensCritique")
    print(f"✅ Source SensCritique, id={source_id}")

    # 3) Récupération des critiques (fake pour l'instant)
    all_reviews = fake_scrape_reviews()
    if limit:
        reviews = all_reviews[:limit]
    else:
        reviews = all_reviews

    print(f"📄 Nombre de critiques à traiter: {len(reviews)}")

    # 4) Boucle principale
    inserted = 0
    skipped = 0
    for row in reviews:
        try:
            print(f"\n▶ Traitement critique URL={row['url']}")

            # 4.1 Upsert film
            film = {
                "titre": row["titre"],
                "url": row["film_url"],
            }
            film_id = upsert_film(conn, film)
            print(f"   🎬 film_id={film_id} ({film['titre']})")

            # 4.2 Enrichissement LLM + embedding
            enriched, emb = enrich_with_llm_and_embedding(row["texte"])
            print("   🧠 enrichissement OK")

            # 4.3 Insertion fact_critique
            before = count_facts(conn)
            insert_review(conn, film_id, source_id, row, enriched, emb)
            after = count_facts(conn)

            if after > before:
                inserted += 1
                print("   ✅ critique insérée")
            else:
                skipped += 1
                print("   ↷ critique déjà présente (hash_critique)")

        except Exception as e:
            print(f"   ❌ ERREUR sur {row['url']}: {e}")

    conn.close()
    print(f"\n📊 Résumé: {inserted} insertions, {skipped} ignorées (déjà en base).")
    print("✅ Pipeline terminé.")


def count_facts(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fact_critique;")
        return cur.fetchone()[0]


if __name__ == "__main__":
    # Quand tu fais "python -m src.flows.weekly_pipeline" dans le conteneur,
    # c'est cette fonction qui est appelée.
    run_weekly(limit=10)
