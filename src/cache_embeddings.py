import hashlib
import json

import numpy as np


def huella_textos(textos):
    huella = hashlib.sha256()

    for texto in textos:
        contenido = str(texto).encode("utf-8")
        huella.update(len(contenido).to_bytes(8, "big"))
        huella.update(contenido)

    return huella.hexdigest()


def guardar_metadatos(ruta_json, textos, modelo, dimension):
    metadatos = {
        "huella_textos": huella_textos(textos),
        "documentos": len(textos),
        "modelo": modelo,
        "dimension": int(dimension)
    }

    with open(ruta_json, "w", encoding="utf-8") as archivo:
        json.dump(metadatos, archivo, indent=2, ensure_ascii=False)


def verificar_cache(ruta_npy, ruta_json, textos, modelo):
    try:
        with open(ruta_json, encoding="utf-8") as archivo:
            datos = json.load(archivo)

        if not isinstance(datos, dict):
            return False

        if (datos.get("huella_textos") != huella_textos(textos)
                or datos.get("documentos") != len(textos)
                or datos.get("modelo") != modelo):
            return False

        embeddings = np.load(ruta_npy, mmap_mode="r", allow_pickle=False)

        return (
            isinstance(embeddings, np.ndarray)
            and embeddings.ndim == 2
            and embeddings.shape == (len(textos), datos.get("dimension"))
            and embeddings.shape[1] > 0
            and np.issubdtype(embeddings.dtype, np.floating)
            and np.isfinite(embeddings).all()
        )

    except (OSError, ValueError, EOFError):
        return False
