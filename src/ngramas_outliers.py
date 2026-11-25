import re
from collections import Counter
from functools import lru_cache

import pandas as pd


STOPWORDS = {
    "es": {
        "a", "al", "de", "del", "el", "la", "las", "los",
        "un", "una", "unos", "unas", "y", "o", "en",
        "con", "por", "para", "que", "se", "su", "sus",
        "es", "son", "fue", "era", "muy", "habia",
        "había", "mucho", "mucha", "muchos", "muchas"
    },
    "en": {
        "a", "an", "the", "and", "or", "of", "to",
        "in", "on", "at", "for", "with", "is",
        "are", "was", "were", "it", "this", "that",
        "very", "there", "had", "have", "has"
    }
}


@lru_cache(maxsize=1)
def stopwords_bilingues():
    from spacy.lang.en.stop_words import STOP_WORDS as stop_en
    from spacy.lang.es.stop_words import STOP_WORDS as stop_es

    return STOPWORDS["es"] | STOPWORDS["en"] | stop_en | stop_es | {
        "i", "me", "my", "we", "our",
        "you", "your", "they", "them", "their",
        "he", "she", "do", "does", "did",
        "be", "been", "being", "would",
        "could", "should", "but", "as",
        "from", "by", "about", "so", "like"
    }


def tokenizar(texto, idioma="es", bilingue=False, lematizar=False):
    if idioma not in STOPWORDS:
        raise ValueError(f"Idioma no soportado para ngramas: {idioma}")

    if not isinstance(texto, str):
        return []

    if lematizar:
        from src.lematizacion import lematizar_texto

        if bilingue:
            from src.idioma_lexico import detectar_idioma_lexico

            idioma = detectar_idioma_lexico(texto, predeterminado=idioma)

        palabras = lematizar_texto(texto, idioma=idioma)
    else:
        palabras = re.findall(r"[^\W\d_]+", texto.lower())

    vacias = stopwords_bilingues() if bilingue else STOPWORDS[idioma]

    return [
        palabra for palabra in palabras
        if palabra not in vacias
        and (not bilingue or len(palabra) > 1)
    ]


def analizar_ngramas(textos, idioma="es", max_resultados=30,
                     bilingue=False, lematizar=False):
    conteos = {n: Counter() for n in (1, 2, 3)}

    for texto in textos:
        palabras = tokenizar(texto, idioma, bilingue, lematizar)

        for n in conteos:
            secuencias = zip(*(palabras[i:] for i in range(n)))
            conteos[n].update(" ".join(secuencia) for secuencia in secuencias)

    filas = []

    for n, tipo in enumerate(("unigrama", "bigrama", "trigrama"), start=1):
        for expresion, frecuencia in conteos[n].most_common(max_resultados):
            filas.append({
                "tipo": tipo,
                "expresion": expresion,
                "frecuencia": frecuencia
            })

    return pd.DataFrame(filas, columns=["tipo", "expresion", "frecuencia"])
