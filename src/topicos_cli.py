import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize


SEMILLA = 42
MIN_DOCUMENTOS = 15


def detectar_topicos(embeddings, minimo=MIN_DOCUMENTOS):
    vectores = np.asarray(embeddings, dtype=np.float32)
    columnas = ["indice", "topico", "estado"]

    if vectores.ndim != 2 or vectores.shape[1] == 0:
        raise ValueError("Los embeddings deben tener dos dimensiones válidas")

    if not isinstance(minimo, (int, np.integer)) or minimo < 3:
        raise ValueError("El mínimo debe ser un entero mayor o igual a 3")

    n_documentos = len(vectores)

    if n_documentos == 0:
        return pd.DataFrame(columns=columnas)

    if not np.isfinite(vectores).all():
        raise ValueError("Los embeddings contienen valores no válidos")

    if n_documentos < minimo:
        return pd.DataFrame({
            "indice": np.arange(n_documentos),
            "topico": -1,
            "estado": "muestra_insuficiente"
        })

    import faiss
    import igraph as ig
    from xidootopic import UMAPReducer, LeidenClusterer

    dimensiones = min(5, n_documentos - 2)

    reductor = UMAPReducer(
        n_neighbors=min(15, n_documentos - 1),
        n_components=dimensiones,
        metric="cosine",
        random_state=SEMILLA
    )

    reducidos = np.asarray(reductor.fit_transform(vectores), dtype=np.float32)

    if reducidos.shape != (n_documentos, dimensiones):
        raise ValueError("Las dimensiones de UMAP no coinciden")

    if not np.isfinite(reducidos).all():
        raise ValueError("UMAP produjo valores no válidos")

    normalizados = np.ascontiguousarray(
        normalize(reducidos, norm="l2"), dtype=np.float32
    )

    indice_faiss = faiss.IndexFlatIP(normalizados.shape[1])
    indice_faiss.add(normalizados)

    vecinos_grafo = min(10, n_documentos - 1)

    _, vecinos = indice_faiss.search(normalizados, vecinos_grafo + 1)

    if vecinos.shape != (n_documentos, vecinos_grafo + 1):
        raise ValueError("Dimensiones de vecinos incorrectas")

    if np.any((vecinos < 0) | (vecinos >= n_documentos)):
        raise ValueError("FAISS devolvió índices no válidos")

    aristas = {
        tuple(sorted((i, int(j))))
        for i, fila in enumerate(vecinos)
        for j in fila
        if i != j
    }

    grafo = ig.Graph(n=n_documentos, edges=sorted(aristas), directed=False)

    modelo = LeidenClusterer(
        resolution=1.0,
        use_weights=False,
        random_state=SEMILLA,
        verbose=False
    )

    etiquetas = np.asarray(modelo.fit_predict(grafo))

    if etiquetas.shape != (n_documentos,):
        raise ValueError("El número de etiquetas no coincide con los documentos")

    if not np.issubdtype(etiquetas.dtype, np.integer):
        raise ValueError("Las etiquetas de Leiden deben ser enteras")

    return pd.DataFrame({
        "indice": np.arange(n_documentos),
        "topico": etiquetas.astype(int),
        "estado": "comunidad_detectada"
    })
