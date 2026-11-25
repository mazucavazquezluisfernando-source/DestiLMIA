from collections import Counter

import pandas as pd

from src.ngramas_outliers import tokenizar


def resumir_comunidades(datos, columna_fuente, etiqueta_dmo,
                       idioma="es", columna_texto="comentario"):
    necesarias = {"topico", columna_texto, "sentimiento", columna_fuente}
    faltantes = necesarias - set(datos.columns)

    if faltantes:
        raise ValueError(f"Columnas faltantes: {sorted(faltantes)}")

    base = datos.loc[
        pd.to_numeric(datos["topico"], errors="coerce") >= 0
    ].reset_index(drop=True)

    base["universo"] = base[columna_fuente].astype(str).eq(
        str(etiqueta_dmo)
    ).map({True: "DMO", False: "Usuarios"})

    if "texto_lexico" in base:
        base["tokens"] = base["texto_lexico"].fillna("").map(
            lambda texto: set(str(texto).split())
        )
    else:
        base["tokens"] = [
            set(tokenizar(texto, idioma=idioma, lematizar=True))
            for texto in base[columna_texto].fillna("").astype(str)
        ]

    def construir(columna):
        filas = []

        for nombre, subconjunto in base.groupby(columna):
            for topico, grupo in subconjunto.groupby("topico"):
                conteo = Counter()

                for palabras in grupo["tokens"]:
                    conteo.update(palabras)

                principales = sorted(
                    conteo.items(), key=lambda x: (-x[1], x[0])
                )[:8]

                palabras_clave = {p for p, _ in principales}
                coincidencias = grupo["tokens"].map(
                    lambda x: len(x & palabras_clave)
                )

                ejemplo = grupo.loc[coincidencias.idxmax(), columna_texto]

                tonos = grupo["sentimiento"].value_counts()
                empatados = tonos[tonos == tonos.max()]
                tono = empatados.index[0] if len(empatados) == 1 else "empate"

                filas.append({
                    "segmento": nombre,
                    "comunidad": int(topico),
                    "documentos": len(grupo),
                    "porcentaje_segmento": round(100 * len(grupo) / len(subconjunto), 1),
                    "tono_predominante": tono,
                    "terminos": ", ".join(f"{p} ({n})" for p, n in principales),
                    "ejemplo_lexico": ejemplo
                })

        return pd.DataFrame(filas, columns=[
            "segmento", "comunidad", "documentos",
            "porcentaje_segmento", "tono_predominante",
            "terminos", "ejemplo_lexico"
        ])

    return construir("universo"), construir(columna_fuente)
