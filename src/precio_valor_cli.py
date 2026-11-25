import re
import unicodedata

import numpy as np
import pandas as pd


CONCEPTOS = {
    "precio_costo": [
        "La entrada al museo es muy cara.",
        "El boleto para visitar la atracción es gratuito.",
        "The admission ticket is expensive.",
        "The museum entrance is affordable."
    ],
    "valor_experiencia": [
        "Visitar el museo valió la pena.",
        "La experiencia turística no valió la pena.",
        "The tourist attraction was worth visiting.",
        "The visit was disappointing and not worth the time."
    ],
    "relacion_calidad_precio": [
        "La experiencia no justificó el dinero pagado.",
        "El lugar ofrece buena relación calidad precio.",
        "The attraction was overpriced for what it offered.",
        "The experience offered good value for money."
    ]
}

PATRON_DINERO = re.compile(
    r"\b(precios?|costos?|cuesta|caro|cara|baratos?|"
    r"gratis|gratuit[oa]|pagar|pagado|dinero|"
    r"price|prices|expensive|cheap|affordable|"
    r"overpriced|money|paid|fees?)\b"
)

PATRON_VALOR = re.compile(
    r"\b(vale la pena|vale pena|valio la pena|"
    r"worth it|worth visiting|not worth it)\b"
)


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return " ".join(texto.split())


def normalizar_vectores(vectores):
    vectores = np.asarray(vectores, dtype=np.float64)

    if (vectores.ndim != 2 or vectores.shape[1] == 0
            or not np.isfinite(vectores).all()):
        raise ValueError("Los embeddings no son válidos")

    normas = np.linalg.norm(vectores, axis=1, keepdims=True)

    if not np.isfinite(normas).all():
        raise ValueError("Normas no finitas")

    return vectores / np.maximum(normas, 1e-12)


def analizar_precio_valor(documentos, sentimientos, embeddings,
                         generar_embeddings, columna_fuente,
                         columna_texto, etiqueta_dmo=None):
    necesarias = {columna_fuente, columna_texto, "es_outlier"}
    faltantes = necesarias - set(documentos.columns)

    if faltantes:
        raise ValueError(f"Columnas faltantes: {sorted(faltantes)}")

    if "sentimiento" not in sentimientos:
        raise ValueError("Falta la columna sentimiento")

    if not sentimientos.index.is_unique:
        raise ValueError("Hay índices de sentimientos duplicados")

    vectores_documentos = normalizar_vectores(embeddings)

    if len(documentos) != len(vectores_documentos):
        raise ValueError("Documentos y embeddings no coinciden")

    if not documentos.index.equals(pd.RangeIndex(len(documentos))):
        raise ValueError("Se necesitan índices originales consecutivos")

    frases = [
        frase for grupo in CONCEPTOS.values() for frase in grupo
    ]

    vectores_referencia = normalizar_vectores(generar_embeddings(frases))

    if vectores_referencia.shape != (len(frases), vectores_documentos.shape[1]):
        raise ValueError("Las dimensiones de embeddings de referencia no coinciden")

    salida = pd.DataFrame({
        "indice_original": documentos.index,
        "fuente": documentos[columna_fuente].astype(str).to_numpy(),
        "texto": documentos[columna_texto].fillna("").astype(str).to_numpy(),
        "es_outlier": documentos["es_outlier"].astype(bool).to_numpy(),
        "sentimiento": sentimientos["sentimiento"].reindex(
            documentos.index
        ).fillna("no_evaluado").to_numpy()
    })

    if etiqueta_dmo is not None:
        salida["universo"] = np.where(
            salida["fuente"].eq(etiqueta_dmo), "DMO", "Usuarios"
        )

    textos = salida["texto"].map(normalizar_texto)
    salida["evidencia_dinero"] = textos.map(lambda t: bool(PATRON_DINERO.search(t)))
    salida["evidencia_valor"] = textos.map(lambda t: bool(PATRON_VALOR.search(t)))

    cercanos = []
    inicio = 0

    for concepto, referencias in CONCEPTOS.items():
        fin = inicio + len(referencias)
        similitudes = vectores_documentos @ vectores_referencia[inicio:fin].T
        mejor_frase = np.argmax(similitudes, axis=1)
        puntuacion = np.max(similitudes, axis=1)

        salida[f"sim_{concepto}"] = puntuacion
        salida[f"frase_{concepto}"] = [referencias[i] for i in mejor_frase]

        mejores = np.argsort(puntuacion)[::-1][:5]

        for posicion, indice in enumerate(mejores, start=1):
            fila = salida.iloc[indice]

            cercanos.append({
                "concepto": concepto,
                "posicion": posicion,
                "indice_original": int(indice),
                "fuente": fila["fuente"],
                "sentimiento": fila["sentimiento"],
                "similitud_coseno": float(puntuacion[indice]),
                "frase_mas_cercana": referencias[mejor_frase[indice]],
                "evidencia_dinero": bool(fila["evidencia_dinero"]),
                "evidencia_valor": bool(fila["evidencia_valor"]),
                "texto": fila["texto"]
            })

        inicio = fin

    resumen = salida.groupby("fuente", as_index=False).agg(
        documentos=("indice_original", "size"),
        candidatos_dinero=("evidencia_dinero", "sum"),
        candidatos_valor=("evidencia_valor", "sum"),
        media_precio=("sim_precio_costo", "mean"),
        mediana_precio=("sim_precio_costo", "median"),
        media_valor=("sim_valor_experiencia", "mean"),
        mediana_valor=("sim_valor_experiencia", "median"),
        media_calidad_precio=("sim_relacion_calidad_precio", "mean")
    )

    resumen["porcentaje_candidatos_dinero"] = (
        resumen["candidatos_dinero"] / resumen["documentos"] * 100
    )

    candidatos = salida.loc[salida["evidencia_dinero"] | salida["evidencia_valor"]]

    distribucion = candidatos.groupby(
        ["fuente", "sentimiento"], as_index=False
    ).size().rename(columns={"size": "candidatos_lexicos"})

    return salida, resumen, pd.DataFrame(cercanos), distribucion


def comparar_precio_universos(detalle, etiqueta_dmo):
    filas = []
    ejemplos = []
    tonos = ("positivo", "negativo", "neutral", "no_evaluado")

    umbrales = {
        concepto: detalle[f"sim_{concepto}"].quantile(0.90)
        for concepto in CONCEPTOS
    }

    es_dmo = detalle["fuente"].eq(etiqueta_dmo)

    for universo, mascara in (("DMO", es_dmo), ("Usuarios", ~es_dmo)):
        grupo = detalle.loc[mascara]
        candidatos = grupo.loc[grupo["evidencia_dinero"] | grupo["evidencia_valor"]]

        fila = {
            "universo": universo,
            "documentos": len(grupo),
            "candidatos_lexicos": len(candidatos),
            "porcentaje_candidatos": 100 * len(candidatos) / len(grupo) if len(grupo) else np.nan
        }

        for tono in tonos:
            fila[tono] = int(candidatos["sentimiento"].eq(tono).sum())

        semanticos = pd.Series(False, index=grupo.index)

        for concepto in CONCEPTOS:
            campo = f"sim_{concepto}"
            cercania = grupo[campo].ge(umbrales[concepto])
            semanticos |= cercania

            fila[f"media_{concepto}"] = grupo[campo].mean()
            fila[f"umbral_p90_{concepto}"] = umbrales[concepto]
            fila[f"candidatos_p90_{concepto}"] = int(cercania.sum())

            for _, texto in grupo.nlargest(5, campo).iterrows():
                ejemplos.append({
                    "universo": universo,
                    "concepto": concepto,
                    "fuente": texto["fuente"],
                    "indice_original": texto["indice_original"],
                    "similitud_coseno": texto[campo],
                    "sentimiento": texto["sentimiento"],
                    "evidencia_lexica": bool(texto["evidencia_dinero"] or texto["evidencia_valor"]),
                    "texto": texto["texto"]
                })

        fila["candidatos_semanticos_p90"] = int(semanticos.sum())
        fila["porcentaje_semanticos_p90"] = 100 * semanticos.mean() if len(grupo) else np.nan

        for tono in tonos:
            fila[f"p90_{tono}"] = int(grupo.loc[semanticos, "sentimiento"].eq(tono).sum())

        filas.append(fila)

    return pd.DataFrame(filas), pd.DataFrame(ejemplos)
