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
