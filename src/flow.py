import os
from .load import get_conn, upsert_film, insert_review
from .transform import enrich_with_llm_and_embedding
from .extract import fake_scrape_reviews


def run_weekly(limit: int = 10):
    """
    Pipeline principal :
      1) Récupère des critiques (fake pour l'instant)
      2) Enrichit via TGI + TEI
      3) Upsert films
      4) Insert reviews (vector)
    """
    print("🚀 Démarrage du pipeline weekly...")

    conn = get_conn(os.getenv("DATABASE_URL"))
    print("✅ Connexion DB OK")

    all_reviews = fake_scrape_reviews()
    reviews = all_reviews[:limit] if limit else all_reviews
    print(f"📄 Nombre de critiques à traiter: {len(reviews)}")

    inserted = 0
    skipped = 0
    for row in reviews:
        try:
            print(f"\n▶ Traitement critique URL={row['url']}")
            film = {
                "film": row["titre"],
                "url": row["film_url"],
            }
            film_id = upsert_film(conn, film)
            print(f"   🎬 film_id={film_id} ({film['film']})")

            enriched, emb = enrich_with_llm_and_embedding(row["texte"])
            print("   🧠 enrichissement OK")

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
    run_weekly(limit=10)
