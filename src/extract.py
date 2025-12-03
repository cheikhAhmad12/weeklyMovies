from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time, hashlib
from bs4 import BeautifulSoup
import pandas as pd
import re

def make_driver(remote_url:str):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    return webdriver.Remote(command_executor=remote_url, options=opts)

def weekly_releases(driver, week_url:str) -> pd.DataFrame:
    driver.get(week_url)
    time.sleep(2.5)  # throttle
    soup = BeautifulSoup(driver.page_source, "html.parser")
    films = []
    # EXEMPLE DE SÉLECTEURS — à ajuster :
    for a in soup.select("a.c-product"):
        titre_el = a.select_one(".c-product__title, .c-entity__title")
        titre = titre_el.get_text(strip=True) if titre_el else None
        url = a.get("href")
        if titre and url and "/film/" in url:
            films.append({"titre": titre, "url": f"https://www.senscritique.com{url}"})
    return pd.DataFrame(films).drop_duplicates(subset=["url"])

def film_reviews(driver, film_url:str) -> pd.DataFrame:
    driver.get(film_url + "/critiques")
    time.sleep(2.5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    rows = []
    # EXEMPLE DE SÉLECTEURS — à ajuster :
    for item in soup.select(".e-critique, .p-critic, article"):
        texte_el = item.select_one(".content, .c-review__body, .rviw")
        texte = texte_el.get_text(" ", strip=True) if texte_el else None
        if not texte: 
            continue
        auteur_el = item.select_one(".author, .c-user__name")
        auteur = auteur_el.get_text(strip=True) if auteur_el else None
        note_el = item.select_one("[data-rating]")
        note = float(note_el["data-rating"]) if note_el and re.match(r"^\d+(\.\d+)?$", note_el["data-rating"]) else None
        hash_c = hashlib.sha1(((auteur or "") + "||" + texte).encode()).hexdigest()
        rows.append({"auteur": auteur, "note": note, "texte": texte, "url": film_url, "hash_critique": hash_c})
    return pd.DataFrame(rows)

def fake_scrape_reviews() -> list[dict]:
    """
    Simule le résultat d'un scraping SensCritique.
    Retourne une liste de critiques factices au format attendu par le flow.
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
    return critiques
