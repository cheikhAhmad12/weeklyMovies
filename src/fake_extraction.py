"""
Fake extraction helpers to test the pipeline without hitting the real website.

Functions mirror the real extraction signatures:
  - weekly_releases(driver, week_url) -> list[dict]
  - film_reviews(driver, film_url, film_title=None) -> list[dict]
  - fake_scrape_reviews() -> list[dict] (convenience)
"""

def weekly_releases(driver=None, week_url: str | None = None) -> list[dict]:
    # driver and week_url are ignored; we return static films.
    return [
        {"titre": "Film test 1", "url": "https://www.senscritique.com/film/film_test_1"},
        {"titre": "Film test 2", "url": "https://www.senscritique.com/film/film_test_2"},
        {"titre": "Film test 3", "url": "https://www.senscritique.com/film/film_test_3"},
    ]


def film_reviews(driver=None, film_url: str = "", film_title: str | None = None) -> list[dict]:
    # Mock reviews keyed by film_url.
    dataset = {
        "https://www.senscritique.com/film/film_test_1": [
            {
                "titre": film_title or "Film test 1",
                "film_url": film_url,
                "auteur": "UserA",
                "note": 8.0,
                "texte": "Film très touchant, avec une réalisation solide et des acteurs convaincants.",
                "url": f"{film_url}/critique/1",
                "hash_critique": "hash-1",
                "likes": 12,
                "comments": 3,
                "rate": 8.2,
                "date_sortie": "2024-01-10",
                "image": "https://img.test/film1.jpg",
                "bande_originale": "Compositeur A",
                "groupe": None,
                "annee": 2024,
                "duree": 110,
                "genres": ["Drame", "Romance"],
                "producteurs": ["Prod A", "Prod B"],
                "realisateurs": ["Réalisateur A"],
                "scenaristes": ["Scénariste A"],
                "pays": ["France"],
            }
        ],
        "https://www.senscritique.com/film/film_test_2": [
            {
                "titre": film_title or "Film test 2",
                "film_url": film_url,
                "auteur": "UserB",
                "note": 6.5,
                "texte": "Comédie correcte, quelques bonnes blagues mais un scénario assez prévisible.",
                "url": f"{film_url}/critique/2",
                "hash_critique": "hash-2",
                "likes": 5,
                "comments": 1,
                "rate": 6.9,
                "date_sortie": "2024-02-20",
                "image": "https://img.test/film2.jpg",
                "bande_originale": "Compositeur B",
                "groupe": None,
                "annee": 2024,
                "duree": 95,
                "genres": ["Comédie"],
                "producteurs": ["Prod C"],
                "realisateurs": ["Réalisateur B"],
                "scenaristes": ["Scénariste B", "Scénariste C"],
                "pays": ["France", "Belgique"],
            }
        ],
        "https://www.senscritique.com/film/film_test_3": [
            {
                "titre": film_title or "Film test 3",
                "film_url": film_url,
                "auteur": "UserC",
                "note": 6.5,
                "texte": "Horreur movie, J ai vraiment eu tres peur.",
                "url": f"{film_url}/critique/3",
                "hash_critique": "hash-3",
                "likes": 2,
                "comments": 0,
                "rate": 7.1,
                "date_sortie": "2023-10-31",
                "image": "https://img.test/film3.jpg",
                "bande_originale": "Compositeur C",
                "groupe": None,
                "annee": 2023,
                "duree": 102,
                "genres": ["Horreur", "Thriller"],
                "producteurs": ["Prod D"],
                "realisateurs": ["Réalisateur C"],
                "scenaristes": ["Scénariste D"],
                "pays": ["États-Unis"],
            }
        ],
    }
    return dataset.get(film_url, [])


def fake_scrape_reviews() -> list[dict]:
    """Aggregates the mock reviews for all fake films."""
    reviews = []
    for film in weekly_releases():
        reviews.extend(film_reviews(film_url=film["url"], film_title=film["titre"]))
    return reviews
