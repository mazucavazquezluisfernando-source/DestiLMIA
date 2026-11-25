import numpy as np
import pandas as pd


def calcular_alineacion(datos, embeddings, columna_fuente, etiqueta_dmo):
    datos = datos.reset_index(drop=True)
    vectores = np.asarray(embeddings, dtype=np.float64)

    if vectores.ndim != 2 or vectores.shape[1] == 0 or len(datos) != len(vectores):
        raise ValueError("Documentos y embeddings no coinciden")

    fuentes = datos[columna_fuente].astype("string").str.strip()
    textos = datos["texto_limpio"].fillna("").astype(str).str.strip()
    normas = np.linalg.norm(vectores, axis=1)

    validos = (fuentes.fillna("").ne("") & textos.ne("")).to_numpy(dtype=bool)
    validos &= np.isfinite(normas) & (normas > 1e-12)

    vectores = vectores[validos] / normas[validos, None]
    fuentes = fuentes[validos].astype(str).to_numpy()

    mascara_dmo = fuentes == etiqueta_dmo.strip()
    dmo = vectores[mascara_dmo]

    centro_dmo = dmo.mean(axis=0) if len(dmo) else None
    norma_dmo = np.linalg.norm(centro_dmo) if centro_dmo is not None else 0.0

    comparaciones = [
        ("global", "TODAS_LAS_FUENTES", ~mascara_dmo)
    ]

    comparaciones.extend(
        ("por_fuente", nombre, fuentes == nombre)
        for nombre in sorted(set(fuentes[~mascara_dmo]))
    )

    resultados = []

    for tipo, nombre, mascara in comparaciones:
        usuarios = vectores[mascara]
        similitud = np.nan

        if not len(dmo) or not len(usuarios):
            estado = "datos_insuficientes"
        else:
            centro = usuarios.mean(axis=0)
            denominador = norma_dmo * np.linalg.norm(centro)

            if denominador <= 1e-12:
                estado = "centroide_no_valido"
            else:
                similitud = float(np.clip(
                    np.dot(centro_dmo, centro) / denominador, -1, 1
                ))
                estado = "calculado"

        resultados.append({
            "tipo": tipo,
            "fuente_percibida": nombre,
            "documentos_dmo": len(dmo),
            "documentos_percibidos": len(usuarios),
            "alineacion_coseno": similitud,
            "estado": estado
        })

    return pd.DataFrame(resultados)
