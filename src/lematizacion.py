from functools import lru_cache

import spacy


MODELOS = {
    "es": "es_core_news_sm",
    "en": "en_core_web_sm"
}


@lru_cache(maxsize=2)
def cargar_modelo(idioma):
    if idioma not in MODELOS:
        raise ValueError(f"Idioma no soportado: {idioma}. Usa 'es' o 'en'.")

    return spacy.load(MODELOS[idioma], disable=["parser", "ner"])


def lematizar_texto(texto, idioma="es"):
    if not isinstance(texto, str):
        return []

    palabras = []

    for token in cargar_modelo(idioma)(texto):
        if token.is_alpha and not token.is_stop:
            lema = (token.lemma_ or token.text).lower()

            if lema.isalpha():
                palabras.append(lema)

    return palabras
