# propiedades/search_config.py
import unicodedata

def norm(s: str) -> str:
    # minúsculas, un solo espacio, sin tildes
    s = (s or "").strip().lower()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))  # saca acentos
    return s

RAW_SYNONYMS = {
    # Escribí lo que te sea cómodo; esto se normaliza igual
    'depto': 'apartamento', 'dpto': 'apartamento', 'dto': 'apartamento', 'ph': 'apartamento',
    'galpon': 'galpón', 'galpón': 'galpón',  # podés repetir, no pasa nada
    'garage': 'cochera', 'garaje': 'cochera',
    'banio': 'baño', 'banios': 'baños', 'banos': 'baños', 'bano': 'baño',
    'lanus': 'lanus', 'lanús': 'lanus',
    # sumá los tuyos...
}

# Pre-normalizamos claves y valores una única vez
SYNONYMS = { norm(k): norm(v) for k, v in RAW_SYNONYMS.items() }
