import os
from src.load import (
    get_conn,
    upsert_film,
    insert_review,
    insert_genres,
    insert_producteurs,
    insert_realisateurs,
    insert_scenaristes,
    insert_pays,
)
from src.transform import sentiment_critique
from src.extract import make_driver, weekly_releases, film_reviews
from src.config import settings

# -------------------------
# 4) Orchestrateur principal
# -------------------------

def run_weekly(limit_films:10):
    """
    Pipeline principal :
      Récupère les films de la semaine (scraping)
      Récupère les critiques de chaque film
      3) Enrichit via sentiment + TEI
      4) Upsert films + insert reviews (vector)
    """
    print(" Démarrage du pipeline weekly...")

    # URLs / drivers
    target_week = os.getenv("WEEK_URL")
    print(f"Target week URL: {target_week}")
    if not target_week:
        raise ValueError("week_url manquant")
    remote = "http://selenium:4444/wd/hub"
    print(f"Connexion Selenium Remote: {remote}")
    driver = make_driver(remote)
    print(f" Driver Selenium OK : {driver}")
    # Connexion DB
    conn = get_conn()
    print("✅ Connexion DB OK")

    try:
        # Récupération des films de la semaine
        films = weekly_releases(driver, target_week)
        if limit_films:
            films = films[:limit_films]
        print(f"🎞️ Films détectés: {len(films)}")
        if not films:
            print("⚠️ Aucun film détecté, arrêt.")
            return

        #Récupération des critiques
        all_reviews: list[dict] = []
        for film in films:
            title = film.get("titre") or film.get("title")
            film_url = film["url"]
            print(f"\n▶ Scraping critiques pour: {title} ({film_url})")
            try:
                reviews = film_reviews(driver, film_url, film_title=title)
                all_reviews.extend(reviews)
                print(f"   📝 Critiques récupérées: {len(reviews)}")
            except Exception as scrape_err:
                print(f"   ❌ Impossible de récupérer les critiques: {scrape_err}")

        print(f"\n📄 Nombre total de critiques à traiter: {len(all_reviews)}")

        # 4) Boucle principale d'insertion
        inserted = 0
        skipped = 0
        for row in all_reviews:
            try:
                print(f"\n▶ Traitement critique URL={row['url']}")
                # Upsert film
                film = {
                    "film": row.get("titre") or row.get("title"),
                    "url": row.get("film_url") or row.get("url"),
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
                insert_genres(conn, film["film"], row.get("genres", []))
                insert_producteurs(conn, film["film"], row.get("producteurs", []))
                insert_realisateurs(conn, film["film"], row.get("realisateurs", []))
                insert_scenaristes(conn, film["film"], row.get("scenaristes", []))
                insert_pays(conn, film["film"], row.get("pays", []))
                sentiment, emb = sentiment_critique(row["texte"])
                print("   😊 Sentiment calculé")

        
                ok = insert_review(conn, film["film"], row, sentiment, emb)
                if not ok:
                    print("⚠️ Critique déjà en base (url).")
                    skipped += 1
                else:
                    print("   ✅ Critique insérée.")
                    inserted += 1
            except Exception as e:
                print(f"❌ ERREUR sur {row.get('url')}: {e}")

        print(f"\n📊 Résumé: {inserted} insertions, {skipped} ignorées.")
        print("✅ Pipeline terminé.")
    finally:
        driver.quit()
        conn.close()


def count_facts(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM reviews;")
        return cur.fetchone()[0]


if __name__ == "__main__":
    run_weekly(limit_films=10)
