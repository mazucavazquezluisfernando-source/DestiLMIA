import re


def limpiar_ligero(texto):
    if not isinstance(texto, str):
        return ""

    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)
    texto = re.sub(r"(?<!\w)\+52[\s.-]*(?:\d[\s.-]*){10}(?!\d)", " ", texto)
    texto = re.sub(r"(?<!\d)\d{10}(?!\d)", " ", texto)
    texto = re.sub(r"#(?=\w)", "", texto)

    return re.sub(r"\s+", " ", texto).strip()
