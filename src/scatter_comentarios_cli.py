from pathlib import Path
from html import escape
import textwrap
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
from sklearn.decomposition import PCA


PALETAS = {
    "viridis": px.colors.sequential.Viridis,
    "cividis": px.colors.sequential.Cividis,
    "plasma": px.colors.sequential.Plasma,
    "inferno": px.colors.sequential.Inferno
}


def proyectar_embeddings(embeddings):
    vectores = np.asarray(embeddings, dtype=float)

    if vectores.ndim != 2 or not np.isfinite(vectores).all():
        raise ValueError("Embeddings invalidos")

    normas = np.linalg.norm(vectores, axis=1)
    vectores = vectores / np.maximum(normas[:, None], 1e-12)

    if min(vectores.shape) < 2:
        return np.zeros((len(vectores), 2))

    return PCA(
        n_components=2,
        svd_solver="randomized",
        random_state=42
    ).fit_transform(vectores)


def codificacion_categorias(datos, categoria, escala):

    categorias = sorted(datos[categoria].astype(str).unique())

    formas = [
        base + forma
        for base in (0, 100, 200, 300)
        for forma in range(25)
    ]

    colores = px.colors.sample_colorscale(
        escala,
        np.linspace(0.08, 0.92, max(2, len(categorias)))
    )

    mapa_colores = dict(zip(categorias, colores))

    mapa_formas = {
        nombre: formas[i % len(formas)]
        for i, nombre in enumerate(categorias)
    }

    return mapa_colores, mapa_formas


def scatter_redundante(
    datos, categoria, escala, titulo,
    eje_x, eje_y, hover, separar_universos
):

    colores, formas = codificacion_categorias(
        datos, categoria, escala
    )

    cantidad = len(formas)

    if cantidad > len(set(formas.values())):
        titulo += " - Formas reutilizadas"

    figura = px.scatter(
        datos,
        x=eje_x,
        y=eje_y,
        color=categoria,
        symbol=categoria,
        color_discrete_map=colores,
        symbol_map=formas,
        facet_col="Universo" if separar_universos else None,
        category_orders={
            "Universo": ["DMO", "Usuarios"]
        } if separar_universos else {},
        facet_col_spacing=0.06,
        hover_data=hover,
        render_mode=(
            "webgl"
            if len(datos) > 2000 and cantidad <= 5
            else "svg"
        ),
        title=titulo
    )

    figura.for_each_annotation(
        lambda a: a.update(
            text=a.text.replace("Universo=", "")
        )
    )

    figura.update_traces(
        marker=dict(size=7, opacity=0.75)
    )

    figura.update_layout(
        height=650,
        hovermode="closest",
        legend=dict(groupclick="togglegroup"),
        hoverlabel=dict(
            bgcolor="#1F2937",
            font=dict(color="white", size=12),
            align="left"
        )
    )

    return figura


def generar_scatter_comentarios(
    datos, sentimientos, topicos, embeddings,
    columna_fuente, columna_texto, ruta, titulo, paleta, etiqueta_dmo=None
):

    datos = datos.copy()
    xy = proyectar_embeddings(embeddings)

    if len(datos) != len(xy):
        raise ValueError("Embeddings y comentarios no coinciden")

    datos["Dimensión 1"] = xy[:, 0]
    datos["Dimensión 2"] = xy[:, 1]

    datos["Sentimiento"] = (
        sentimientos["sentimiento"]
        .reindex(datos.index)
        .fillna("no_evaluado")
        .astype(str)
    )

    mapa = topicos.set_index("indice_original")["topico"]

    datos["Tópico"] = [
        f"Tópico {int(valor)}"
        if pd.notna(valor) and valor >= 0
        else "Sin tópico asignado"
        for valor in datos.index.map(mapa)
    ]

    datos["Fuente"] = datos[columna_fuente].astype(str)
    datos["Universo"] = np.where(datos["Fuente"].eq(etiqueta_dmo), "DMO", "Usuarios") if etiqueta_dmo is not None else datos["Fuente"]

    datos["Estado"] = np.where(
        datos["es_outlier"], "Outlier", "Normal"
    )

    datos["Índice"] = datos.index

    def formatear_comentario(texto):
        texto = " ".join(str(texto).split())

        if len(texto) > 280:
            texto = texto[:277].rstrip() + "..."

        lineas = textwrap.wrap(
            texto,
            width=55,
            break_long_words=True
        )

        return "<br>".join(escape(linea) for linea in lineas)

    datos["Comentario"] = (
        datos[columna_texto]
        .fillna("")
        .astype(str)
        .apply(formatear_comentario)
    )


    if paleta not in PALETAS:
        raise ValueError("Paleta no admitida")


    def graficar(categoria, encabezado):

        return scatter_redundante(
            datos,
            categoria,
            PALETAS[paleta],
            encabezado,
            "Dimensión 1",
            "Dimensión 2",
            [
                "Comentario", "Fuente", "Sentimiento",
                "Tópico", "Universo", "Estado", "Índice"
            ],
            etiqueta_dmo is not None
        )


    figura_fuentes = graficar(
        "Fuente", "Comentarios por fuente y universo"
    )


    figura_topicos = graficar(
        "Tópico", "Comentarios por tópico y universo"
    )


    nota = (
        "Cada punto representa un comentario. "
        "PCA proyecta los embeddings a dos dimensiones. "
        "El color y la forma identifican la misma categoría. "
        "Los paneles distinguen la DMO de los usuarios. "
        "Utiliza la leyenda para aislar categorías. "
        "Con muchas categorías, algunas formas pueden "
        "reutilizarse o resultar difíciles de distinguir. "
        "Los textos atípicos no tienen sentimiento evaluado."
    )


    pagina = (
        "<!doctype html><html lang='es'><head>"
        "<meta charset='utf-8'><title>"
        + escape(titulo)
        + "</title></head><body style='font-family:Arial;"
        "max-width:1200px;margin:25px auto'>"
        + "<h1>" + escape(titulo) + "</h1>"
        + "<p>" + escape(nota) + "</p>"
        + pio.to_html(
            figura_fuentes,
            full_html=False,
            include_plotlyjs=True
        )
        + pio.to_html(
            figura_topicos,
            full_html=False,
            include_plotlyjs=False
        )
        + "</body></html>"
    )

    ruta = Path(ruta)
    ruta.write_text(pagina, encoding="utf-8")

    return {
        "documentos": len(datos),
        "sin_topico": int(
            datos["Tópico"].eq("Sin tópico asignado").sum()
        ),
        "archivo": str(ruta)
    }
