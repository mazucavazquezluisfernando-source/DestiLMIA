import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def comparar_comunidades(datos, embeddings, columna_fuente, etiqueta_dmo):
    columnas = [
        "comunidad_usuarios",
        "comunidad_dmo",
        "documentos_usuarios",
        "documentos_dmo",
        "similitud_coseno"
    ]

    necesarias = {"topico", "indice_original", columna_fuente}
    faltantes = necesarias - set(datos.columns)

    if faltantes:
        raise ValueError(f"Columnas faltantes: {sorted(faltantes)}")

    datos = datos.loc[datos["topico"] >= 0]
    embeddings = np.asarray(embeddings)

    if embeddings.ndim != 2 or embeddings.shape[1] == 0:
        raise ValueError("Embeddings inválidos")

    indices = pd.to_numeric(
        datos["indice_original"], errors="coerce"
    ).to_numpy(dtype=float, na_value=np.nan)

    if (not np.isfinite(indices).all()
            or np.any(indices < 0)
            or np.any(indices >= len(embeddings))
            or np.any(indices != np.floor(indices))):
        raise ValueError("Índices originales inválidos")

    indices = indices.astype(int)

    if len(np.unique(indices)) != len(indices):
        raise ValueError("Hay índices originales duplicados")

    vectores = embeddings[indices]

    if not np.isfinite(vectores).all():
        raise ValueError("Embeddings no finitos")

    es_dmo = datos[columna_fuente].astype(str).str.strip().eq(
        etiqueta_dmo.strip()
    )

    def obtener_centros(grupo_datos, grupo_vectores):
        centros = {}

        for topico, posiciones in grupo_datos.groupby("topico").indices.items():
            v = grupo_vectores[posiciones]
            normas = np.linalg.norm(v, axis=1, keepdims=True)

            if not np.isfinite(normas).all():
                raise ValueError("Normas no finitas")

            v = v / np.maximum(normas, 1e-12)
            centros[int(topico)] = (v.mean(axis=0), len(v))

        return centros

    dmo = obtener_centros(datos.loc[es_dmo], vectores[es_dmo.to_numpy()])
    usuarios = obtener_centros(datos.loc[~es_dmo], vectores[(~es_dmo).to_numpy()])

    resultados = []

    for tema_usuario, (centro_usuario, n_usuarios) in usuarios.items():
        for tema_dmo, (centro_dmo, n_dmo) in dmo.items():
            similitud = cosine_similarity(
                centro_usuario.reshape(1, -1),
                centro_dmo.reshape(1, -1)
            )[0, 0]

            resultados.append({
                "comunidad_usuarios": tema_usuario,
                "comunidad_dmo": tema_dmo,
                "documentos_usuarios": n_usuarios,
                "documentos_dmo": n_dmo,
                "similitud_coseno": float(similitud)
            })

    return pd.DataFrame(resultados, columns=columnas)
