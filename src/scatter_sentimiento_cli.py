from pathlib import Path

import numpy as np
from src.scatter_comentarios_cli import PALETAS, proyectar_embeddings, scatter_redundante


def generar_scatter_sentimiento(
    datos, embeddings, columna_fuente,
    columna_texto, ruta, titulo, paleta, etiqueta_dmo=None
):

    if paleta not in PALETAS:
        raise ValueError("Paleta no admitida")

    ruta = Path(ruta)

    if datos.empty:
        ruta.write_text(
            "<html><body><p>No hay comentarios positivos "
            "o negativos para graficar.</p></body></html>",
            encoding="utf-8"
        )
        return {"documentos": 0, "archivo": str(ruta)}

    datos = datos.copy()
    xy = proyectar_embeddings(embeddings)
    indices = datos["indice_original"].to_numpy(dtype=float)

    if (
        not np.isfinite(indices).all()
        or (indices != np.floor(indices)).any()
        or (indices < 0).any()
        or (indices >= len(xy)).any()
        or len(np.unique(indices)) != len(indices)
    ):
        raise ValueError("Indices originales invalidos")

    indices = indices.astype(int)

    datos["Dimension 1"] = xy[indices, 0]
    datos["Dimension 2"] = xy[indices, 1]

    def describir(fila):
        polaridad = str(fila["polaridad_binaria"]).capitalize()

        if fila["metodo_sentimiento"] == "frecuencias_muestra_pequena":
            return f"{polaridad} - frecuencias"

        return (
            f"{polaridad} - topico "
            f"{int(fila['topico_sentimiento'])}"
        )

    datos["Grupo"] = datos.apply(describir, axis=1)
    datos["Universo"] = np.where(datos[columna_fuente].astype(str).eq(etiqueta_dmo), "DMO", "Usuarios") if etiqueta_dmo is not None else datos[columna_fuente].astype(str)


    figura = scatter_redundante(
        datos,
        "Grupo",
        PALETAS[paleta],
        f"{titulo} - Tópicos por polaridad binaria y universo",
        "Dimension 1",
        "Dimension 2",
        [
            columna_texto,
            columna_fuente,
            "sentimiento",
            "polaridad_binaria",
            "binaria_derivada_de_neutral",
            "metodo_sentimiento",
            "Universo"
        ],
        etiqueta_dmo is not None
    )


    figura.update_traces(
        marker=dict(size=10, opacity=0.8)
    )

    figura.write_html(
        ruta,
        include_plotlyjs=True
    )

    return {
        "documentos": len(datos),
        "archivo": str(ruta)
    }
