from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time, hashlib, json
from bs4 import BeautifulSoup
import re
import requests

def make_driver(remote_url:str):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    return webdriver.Remote(command_executor=remote_url, options=opts)

def weekly_releases(driver, week_url:str) -> list[dict]:
    driver.get(week_url)
    time.sleep(2.5)  # throttle
    soup = BeautifulSoup(driver.page_source, "html.parser")
    films = []
    # Sélecteurs élargis : certaines pages listent les films via d'autres classes.
    anchors = soup.select(
        "a.c-product, a[href*='/film/'].elco-anchor, a[href*='/film/'].c-entity, a[href*='/film/']"
    )
    for a in anchors:
        titre_el = a.select_one(".c-product__title, .c-entity__title, .elco-entity-title, h2, .title")
        titre = titre_el.get_text(strip=True) if titre_el else a.get_text(strip=True)
        url = a.get("href")
        if titre and url and "/film/" in url:
            if not url.startswith("http"):
                url = f"https://www.senscritique.com{url}"
            films.append({"titre": titre, "url": url})
    # dedupe while preserving order
    seen = set()
    deduped = []
    for film in films:
        if film["url"] in seen:
            continue
        seen.add(film["url"])
        deduped.append(film)
    return deduped

def film_reviews(driver, film_url:str, film_title: str | None = None) -> list[dict]:
    driver.get(film_url + "/critiques")
    time.sleep(2.5)
    html_source = driver.page_source
    soup = BeautifulSoup(html_source, "html.parser")
    rows = []

    def parse_next_data_reviews(soup_obj):
        """
        SensCritique est en Next.js : les critiques sont dans le JSON __NEXT_DATA__/__APOLLO_STATE__.
        On extrait directement ces données pour éviter de dépendre des classes CSS dynamiques.
        """
        script_tag = soup_obj.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            return []
        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError:
            return []

        apollo = (
            data.get("props", {})
                .get("pageProps", {})
                .get("__APOLLO_STATE__", {})
        )
        if not isinstance(apollo, dict):
            return []

        # On récupère un bloc Product pour métadonnées éventuelles (note moyenne, image, dates).
        product_node = None
        for key, val in apollo.items():
            if isinstance(val, dict) and key.startswith("Product:"):
                product_node = val
                break

        # Cherche les références de critiques depuis le bloc Product (clé reviews({...})) ou n'importe quel node Reviews.
        review_refs = []
        if product_node:
            for k, v in product_node.items():
                if isinstance(v, dict) and v.get("__typename") == "Reviews" and "items" in v:
                    for item in v.get("items", []):
                        ref = item.get("__ref") if isinstance(item, dict) else None
                        if ref and ref.startswith("Review:"):
                            review_refs.append(ref)
        # fallback : scan global si non trouvé
        if not review_refs:
            for node in apollo.values():
                if isinstance(node, dict) and node.get("__typename") == "Reviews" and "items" in node:
                    for item in node.get("items", []):
                        ref = item.get("__ref") if isinstance(item, dict) else None
                        if ref and ref.startswith("Review:"):
                            review_refs.append(ref)
        if not review_refs:
            return []

        film_rate = product_node.get("rating") if product_node else None
        date_sortie = product_node.get("dateRelease") if product_node else None
        image = None
        if product_node:
            for k, v in product_node.items():
                # Exemple de clé: medias({"backdropSize":"1200"})
                if isinstance(v, dict) and "picture" in v:
                    image = v.get("picture")
                    break

        parsed = []
        seen_hashes = set()
        for ref in review_refs:
            review_obj = apollo.get(ref, {})
            if not isinstance(review_obj, dict):
                continue
            texte = review_obj.get("bodyShort") or review_obj.get("body") or ""
            if not texte:
                continue
            auteur = None
            author_ref = review_obj.get("author", {}).get("__ref")
            if author_ref and isinstance(apollo.get(author_ref), dict):
                user = apollo[author_ref]
                auteur = user.get("name") or user.get("username")
            note = review_obj.get("rating")
            review_url = review_obj.get("url")
            full_review_url = (
                review_url if review_url and review_url.startswith("http")
                else f"https://www.senscritique.com{review_url}" if review_url else film_url
            )
            hash_c = hashlib.sha1(((auteur or "") + "||" + texte).encode()).hexdigest()
            if hash_c in seen_hashes:
                continue
            seen_hashes.add(hash_c)
            parsed.append({
                "titre": film_title,
                "film_url": film_url,
                "auteur": auteur,
                "note": note,
                "texte": texte,
                "url": full_review_url,
                "hash_critique": hash_c,
                "likes": review_obj.get("likeCount"),
                "comments": review_obj.get("commentCount"),
                "rate": film_rate,
                "date_sortie": date_sortie,
                "image": image,
                "bande_originale": None,
                "groupe": None,
                "annee": product_node.get("yearOfProduction") if product_node else None,
                "duree": product_node.get("duration") if product_node else None,
                "genres": [],
                "producteurs": [],
                "realisateurs": [],
                "scenaristes": [],
                "pays": [],
            })
        return parsed

    # Essaye d'abord via le JSON Next.js, puis fallback sur le scraping classique.
    rows = parse_next_data_reviews(soup)
    if not rows:
        # Fallback réseau direct (au cas où Cloudflare/lazy load empêche page_source de contenir le JSON)
        try:
            resp = requests.get(film_url + "/critiques", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
            if resp.ok:
                soup_fallback = BeautifulSoup(resp.text, "html.parser")
                rows = parse_next_data_reviews(soup_fallback)
        except Exception:
            pass

    if rows:
        return rows

    # Sélecteurs élargis pour s'adapter aux variantes de pages critiques.
    for item in soup.select(".e-critique, .p-critic, article, [data-testid='review-card'], .rviw"):
        texte_el = item.select_one(".content, .c-review__body, .rviw, [data-testid='review-body']")
        texte = texte_el.get_text(" ", strip=True) if texte_el else None
        if not texte: 
            continue
        auteur_el = item.select_one(".author, .c-user__name")
        auteur = auteur_el.get_text(strip=True) if auteur_el else None
        note_el = item.select_one("[data-rating]")
        note = float(note_el["data-rating"]) if note_el and re.match(r"^\d+(\.\d+)?$", note_el["data-rating"]) else None
        hash_c = hashlib.sha1(((auteur or "") + "||" + texte).encode()).hexdigest()
        review_link = item.select_one("a[href*='/critique/'], a[href*='/review/']")
        review_url = review_link.get("href") if review_link else None
        full_review_url = (
            review_url
            if review_url and review_url.startswith("http")
            else f"https://www.senscritique.com{review_url}" if review_url else film_url
        )
        rows.append({
            "titre": film_title,
            "film_url": film_url,
            "auteur": auteur,
            "note": note,
            "texte": texte,
            "url": full_review_url,
            "hash_critique": hash_c,
            # champs attendus par le reste du pipeline
            "likes": None,
            "comments": None,
            "rate": None,
            "date_sortie": None,
            "image": None,
            "bande_originale": None,
            "groupe": None,
            "annee": None,
            "duree": None,
            "genres": [],
            "producteurs": [],
            "realisateurs": [],
            "scenaristes": [],
            "pays": [],
        })
    return rows


def fake_scrape_reviews() -> list[dict]:
    """
    Simule le résultat d'un scraping SensCritique, adapté au schéma actuel.
    Retourne une liste de dicts contenant :
      - métadonnées film (film_url, rate, date_sortie, image, bande_originale, groupe, annee, duree, genres, producteurs, realisateurs, scenaristes, pays)
      - champs critique (titre, texte, url, likes, comments, note)
    """
    critiques = []

    def make_hash(texte, url):
        return hashlib.md5(f"{texte}|{url}".encode("utf-8")).hexdigest()

    critiques.append({
        "titre": "Film test 1",
        "film_url": "https://www.senscritique.com/film/film_test_1",
        "auteur": "UserA",
        "note": 8.0,
        "texte": "Film très touchant, avec une réalisation solide et des acteurs convaincants.",
        "url": "https://www.senscritique.com/film/film_test_1/critique/1",
        "hash_critique": make_hash("Film très touchant, avec une réalisation solide et des acteurs convaincants.", "https://www.senscritique.com/film/film_test_1/critique/1"),
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
    })

    critiques.append({
        "titre": "Film test 2",
        "film_url": "https://www.senscritique.com/film/film_test_2",
        "auteur": "UserB",
        "note": 6.5,
        "texte": "Comédie correcte, quelques bonnes blagues mais un scénario assez prévisible.",
        "url": "https://www.senscritique.com/film/film_test_2/critique/2",
        "hash_critique": make_hash("Comédie correcte, quelques bonnes blagues mais un scénario assez prévisible.", "https://www.senscritique.com/film/film_test_2/critique/2"),
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
    })

    critiques.append({
        "titre": "Film test 3",
        "film_url": "https://www.senscritique.com/film/film_test_3",
        "auteur": "UserC",
        "note": 6.5,
        "texte": "Horreur movie, J ai vraiment eu tres peur.",
        "url": "https://www.senscritique.com/film/film_test_3/critique/3",
        "hash_critique": make_hash("Horreur movie, J ai vraiment eu tres peur.", "https://www.senscritique.com/film/film_test_3/critique/3"),
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
    })
    return critiques
