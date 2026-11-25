import numpy as np


def detectar_outliers(embeddings, vecinos=5, multiplicador=3.0, bloque=256):
    vectores = np.asarray(embeddings, dtype=np.float32)

    if vectores.ndim != 2 or vectores.shape[1] == 0:
        raise ValueError("Embeddings inválidos")

    n = len(vectores)

    if n < 3:
        raise ValueError("Se requieren al menos 3 documentos")

    if not np.isfinite(vectores).all():
        raise ValueError("Embeddings no finitos")

    if any(not isinstance(p, (int, np.integer)) or p < 1
           for p in (vecinos, bloque)):
        raise ValueError("Vecinos y bloque deben ser enteros positivos")

    if (not isinstance(multiplicador, (int, float, np.integer, np.floating))
            or not np.isfinite(multiplicador) or multiplicador <= 0):
        raise ValueError("Multiplicador inválido")

    normas = np.linalg.norm(vectores, axis=1, keepdims=True)

    if not np.isfinite(normas).all():
        raise ValueError("Normas no finitas")

    vectores = vectores / np.maximum(normas, 1e-12)
    k = min(vecinos, n - 1)
    similitud = np.empty(n, dtype=float)

    for inicio in range(0, n, bloque):
        fin = min(inicio + bloque, n)
        matriz = vectores[inicio:fin] @ vectores.T

        np.clip(matriz, -1, 1, out=matriz)
        matriz[np.arange(fin - inicio), np.arange(inicio, fin)] = -np.inf
        matriz.partition(n - k, axis=1)

        similitud[inicio:fin] = matriz[:, -k:].mean(axis=1)

    mediana = float(np.median(similitud))
    mad = float(np.median(np.abs(similitud - mediana)))
    umbral = mediana - max(multiplicador * 1.4826 * mad, 1e-6)
    puntuaciones = similitud - umbral
    mascara = puntuaciones < 0

    return {
        "es_outlier": mascara,
        "es_normal": ~mascara,
        "puntuacion_anomalia": puntuaciones,
        "similitud_vecinos": similitud,
        "metodo": "vecinos_coseno_mad",
        "vecinos": int(k),
        "multiplicador": float(multiplicador),
        "mediana": mediana,
        "mad": mad,
        "umbral": float(umbral),
        "proporcion_atipicos": float(mascara.mean())
    }
