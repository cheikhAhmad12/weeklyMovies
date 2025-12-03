import requests

def embed_texts(texts:list[str], tei_url:str) -> list[list[float]]:
    r = requests.post(f"{tei_url}/embed", json={"inputs": texts, "truncate": True})
    r.raise_for_status()
    data = r.json()
    # TEI peut renvoyer {"embeddings":[...]} ou liste directe selon version
    return data["embeddings"] if isinstance(data, dict) else data
