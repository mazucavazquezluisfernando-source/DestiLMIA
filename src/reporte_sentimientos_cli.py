import pandas as pd


def resumir_sentimientos(datos, columna_fuente, etiqueta_dmo):
    necesarias = {
        columna_fuente,
        "sentimiento",
        "polaridad_binaria",
        "binaria_derivada_de_neutral"
    }

    faltantes = necesarias.difference(datos.columns)

    if faltantes:
        raise ValueError(f"Columnas faltantes: {sorted(faltantes)}")

    base = datos.copy()
    es_dmo = base[columna_fuente].astype(str).eq(str(etiqueta_dmo))
    base["tipo_imagen"] = es_dmo.map({True: "DMO", False: "Usuarios"})

    def agrupar(columna):
        resumen = base.groupby(columna).agg(
            documentos=("sentimiento", "size"),
            positivos=("sentimiento", lambda x: x.eq("positivo").sum()),
            negativos=("sentimiento", lambda x: x.eq("negativo").sum()),
            neutrales=("sentimiento", lambda x: x.eq("neutral").sum()),
            binarios_positivos=("polaridad_binaria", lambda x: x.eq("positivo").sum()),
            binarios_negativos=("polaridad_binaria", lambda x: x.eq("negativo").sum()),
            binarios_desde_neutral=("binaria_derivada_de_neutral", "sum")
        ).reset_index()

        resumen["porcentaje_neutral"] = (
            100 * resumen["neutrales"] / resumen["documentos"]
        ).round(1)

        clases = resumen[["positivos", "negativos", "neutrales"]]

        resumen["tono_predominante"] = clases.apply(
            lambda fila: fila.idxmax() if (fila == fila.max()).sum() == 1 else "empate",
            axis=1
        )

        return resumen

    return agrupar(columna_fuente), agrupar("tipo_imagen")
