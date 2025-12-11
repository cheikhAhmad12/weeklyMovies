import os
import re
import requests

try:
    from huggingface_hub import InferenceClient  # optional
except ImportError:
    InferenceClient = None


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
    model = model_id or os.getenv("SENTIMENT_MODEL") or os.getenv("GEN_MODEL")
    token = hf_token or os.getenv("HF_TOKEN")

    if InferenceClient and token and model:
        try:
            gen_client = InferenceClient(model=model, token=token, timeout=120)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Classifie le sentiment du texte en 'positif', 'negatif' ou 'neutre'. "
                        "Réponds uniquement par l'un de ces trois mots."
                    ),
                },
                {"role": "user", "content": text},
            ]
            resp = gen_client.chat_completion(
                messages=messages,
                max_tokens=16,
                temperature=0.2,
                top_p=0.9,
            )
            m = resp.choices[0].message
            label = (m["content"] if isinstance(m, dict) else m.content).strip().lower()
            if "neg" in label:
                return "negatif"
            if "pos" in label:
                return "positif"
            if "neut" in label:
                return "neutre"
        except Exception:
            return None

    # Si pas de client/token/modèle ou échec de l'appel HF, on retourne None pour signaler l'absence de résultat LLM.
    return None


def sentiment_critique(texte: str, tei_url: str | None = None):
    try:
        emb = embed_texts([texte], tei_url)[0]
    except Exception:
        emb = None
    sentiment = classify_sentiment_hf(texte)
    print (f"Sentiment critique: {sentiment}")
    return sentiment, emb
