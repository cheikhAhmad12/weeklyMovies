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
