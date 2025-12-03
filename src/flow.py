from .load import (
    get_conn,
    upsert_film,
    insert_review,
    insert_genres,
    insert_producteurs,
    insert_realisateurs,
    insert_scenaristes,
    insert_pays,
)
from .transform import enrich_with_llm_and_embedding
from .extract import fake_scrape_reviews

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
                "rate": row.get("rate"),
                "date_sortie": row.get("date_sortie"),
                "image": row.get("image"),
                "bande_originale": row.get("bande_originale"),
                "groupe": row.get("groupe"),
                "annee": row.get("annee"),
                "duree": row.get("duree"),
            }
            film_id = upsert_film(conn, film)
            print(f"   🎬 film_id={film_id} ({film['film']})")

            # 3.2 Dimensions liées au film
            insert_genres(conn, film["film"], row.get("genres", []))
            insert_producteurs(conn, film["film"], row.get("producteurs", []))
            insert_realisateurs(conn, film["film"], row.get("realisateurs", []))
            insert_scenaristes(conn, film["film"], row.get("scenaristes", []))
            insert_pays(conn, film["film"], row.get("pays", []))

            # 3.3 Enrichissement LLM + embedding
            enriched, emb = enrich_with_llm_and_embedding(row["texte"])
            print("   🧠 enrichissement OK")

            # 3.4 Insertion review
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
    # Quand tu fais "python -m src.flow" dans le conteneur,
    # c'est cette fonction qui est appelée.
    run_weekly(limit=10)
