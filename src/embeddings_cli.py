import os
from functools import lru_cache

import numpy as np

from src.generar_embeddings import dividir_texto


MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def cargar_modelo_local():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELO, local_files_only=True)


def generar_embeddings(textos, batch_size=64):
    if isinstance(textos, str):
        raise ValueError("Se requiere una colección de documentos.")

    textos = list(textos)

    if not textos:
        raise ValueError("No se recibieron documentos.")

    if any(not isinstance(t, str) or not t.strip() for t in textos):
        raise ValueError("Hay textos vacíos o inválidos.")

    modelo = cargar_modelo_local()
    fragmentos = []
    indices = []

    for indice, texto in enumerate(textos):
        partes = dividir_texto(texto, modelo.tokenizer, modelo.max_seq_length)

        if not partes:
            raise ValueError("Hay documentos sin fragmentos.")

        fragmentos.extend(partes)
        indices.extend([indice] * len(partes))

    vectores = modelo.encode(
        fragmentos,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    if (vectores.ndim != 2
            or vectores.shape[0] != len(fragmentos)
            or vectores.shape[1] == 0
            or not np.issubdtype(vectores.dtype, np.floating)
            or not np.isfinite(vectores).all()):
        raise ValueError("Embeddings de fragmentos inválidos.")

    resultado = np.zeros((len(textos), vectores.shape[1]), dtype=np.float32)
    conteos = np.zeros(len(textos), dtype=np.int64)

    np.add.at(resultado, indices, vectores)
    np.add.at(conteos, indices, 1)

    resultado /= conteos[:, None]

    if not np.isfinite(resultado).all():
        raise ValueError("Se generaron embeddings inválidos.")

    return resultado
