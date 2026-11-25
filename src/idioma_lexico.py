import re
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder


@lru_cache(maxsize=1)
def cargar_detector():
    return LanguageDetectorBuilder.from_languages(
        Language.SPANISH, Language.ENGLISH
    ).build()


def detectar_idioma_lexico(texto, predeterminado="es"):
    if predeterminado not in ("es", "en"):
        raise ValueError("Idioma no soportado")

    if not isinstance(texto, str):
        return predeterminado

    if len(re.findall(r"[^\W\d_]+", texto)) < 5:
        return predeterminado

    idioma = cargar_detector().detect_language_of(texto)

    if idioma == Language.SPANISH:
        return "es"

    if idioma == Language.ENGLISH:
        return "en"

    return predeterminado
