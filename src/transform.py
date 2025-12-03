import requests, json, re

def summarize_and_tag(text: str, tgi_url: str):
    prompt = (
        "Tu es un analyste cinéma. Résume la critique en 2 phrases, "
        "donne un sentiment (positif|neutre|négatif) et 3-5 thèmes (mots courts). "
        "Réponds en JSON avec les clés: resume, sentiment, themes.\n"
        f"Critique:\n{text}\n"
    )
    r = requests.post(
        f"{tgi_url}/generate",
        json={"inputs": prompt, "parameters": {"temperature": 0.2, "max_new_tokens": 200}}
    )
    r.raise_for_status()
    out = r.json()
    raw = out.get("generated_text", out[0]["generated_text"] if isinstance(out, list) else "")
    m = re.search(r"\{.*\}", raw, re.S)
    js = json.loads(m.group(0)) if m else {"resume":"", "sentiment":"neutre", "themes":[]}
    return js

def embed_texts(texts:list[str], tei_url:str) -> list[list[float]]:
    r = requests.post(f"{tei_url}/embed", json={"inputs": texts, "truncate": True})
    r.raise_for_status()
    data = r.json()
    # TEI peut renvoyer {"embeddings":[...]} ou liste directe selon version
    return data["embeddings"] if isinstance(data, dict) else data

def enrich_with_llm_and_embedding(texte: str, tgi_url: str | None = None, tei_url: str | None = None):
    """
    Combine appel TGI (résumé/sentiment/thèmes) et embedding TEI sur un texte.
    """
    tgi = tgi_url or "http://tgi:80"
    tei = tei_url or "http://tei:80"
    enriched = summarize_and_tag(texte, tgi)
    emb = embed_texts([texte], tei)[0]
    return enriched, emb
