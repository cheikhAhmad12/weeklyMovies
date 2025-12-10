import os
import re
import requests


def embed_texts(texts: list[str], tei_url: str | None = None) -> list[list[float]]:
    """
    Appelle TEI pour obtenir des embeddings.
    """
    tei = tei_url or os.getenv("TEI_URL") or "http://tei:80"
    r = requests.post(f"{tei}/embed", json={"inputs": texts, "truncate": True}, timeout=60)
    r.raise_for_status()
    data = r.json()
    # TEI peut renvoyer {"embeddings":[...]} ou une liste directe selon la version
    return data["embeddings"] if isinstance(data, dict) else data


def classify_sentiment_hf(text: str, model_id: str | None = None, hf_token: str | None = None) -> str | None:
    """
    Utilise l'API Hugging Face Inference pour classifier le sentiment si un token est dispo.
    Fallback sur une heuristique locale pour rester offline-friendly.
    """
    model = model_id or os.getenv("SENTIMENT_MODEL") or os.getenv("GEN_MODEL") or "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    token = hf_token or os.getenv("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if token:
        try:
            resp = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers=headers,
                json={"inputs": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            # Réponse typique: [[{"label": "NEGATIVE", "score": ...}, ...]]
            if isinstance(data, list):
                first = data[0][0] if data and isinstance(data[0], list) else data[0]
                label = first.get("label", "") if isinstance(first, dict) else ""
            elif isinstance(data, dict):
                label = data.get("label", "")
            else:
                label = ""
            lbl = label.lower()
            if re.search(r"neg", lbl):
                return "negatif"
            if re.search(r"pos", lbl):
                return "positif"
            if re.search(r"neu", lbl):
                return "neutre"
        except Exception:
            # on tombe sur le fallback heuristique
            pass

    # Fallback léger sans appel réseau
    txt = text.lower()
    positives = {"excellent", "bien", "super", "magnifique", "touchant", "drôle", "genial", "très bien", "tres bien"}
    negatives = {"mauvais", "nul", "décevant", "decevant", "lent", "ennuyeux", "horrible", "pire"}
    pos_hits = sum(1 for w in positives if w in txt)
    neg_hits = sum(1 for w in negatives if w in txt)
    if pos_hits > neg_hits and pos_hits > 0:
        return "positif"
    if neg_hits > pos_hits and neg_hits > 0:
        return "negatif"
    return "neutre" if text else None


def sentiment_critique(texte: str, tei_url: str | None = None):
    """
    Enrichit une critique avec un embedding TEI et un label de sentiment via l'API HF.
    """
    tei = tei_url or os.getenv("TEI_URL") or "http://tei:80"
    try:
        emb = embed_texts([texte], tei)[0]
    except Exception:
        emb = None
    sentiment = classify_sentiment_hf(texte)
    enriched = {"resume": None, "sentiment": sentiment, "themes": []}
    return enriched, emb
