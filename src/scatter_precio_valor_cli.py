from pathlib import Path
from html import escape
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
from src.scatter_comentarios_cli import PALETAS


CONCEPTOS = [
    (
        "precio_costo",
        "sim_precio_costo",
        "Precio y costo"
    ),
    (
        "valor_experiencia",
        "sim_valor_experiencia",
        "Valor de la experiencia"
    ),
    (
        "relacion_calidad_precio",
        "sim_relacion_calidad_precio",
        "Relación calidad-precio"
    )
]


def generar_scatter_precio_valor(
    detalle, cercanos, ruta, titulo, paleta
):

    datos = detalle.copy()

    if datos.empty:
        raise ValueError("No hay documentos para visualizar")

    columnas = {
        "indice_original", "fuente", "texto",
        "sentimiento", "es_outlier",
        "evidencia_dinero", "evidencia_valor"
    }

    columnas.update(c[1] for c in CONCEPTOS)

    if not columnas.issubset(datos.columns):
        raise ValueError("Faltan columnas del análisis económico")

    if datos["indice_original"].duplicated().any():
        raise ValueError("Hay índices originales duplicados")

    for _, columna, _ in CONCEPTOS:
        datos[columna] = pd.to_numeric(
            datos[columna], errors="raise"
        )

        if not np.isfinite(datos[columna]).all():
            raise ValueError("Existen similitudes no finitas")

    def es_verdadero(serie):
        return (
            serie.astype(str)
            .str.lower()
            .isin(["true", "1"])
        )

    evidencia = (
        es_verdadero(datos["evidencia_dinero"])
        | es_verdadero(datos["evidencia_valor"])
    )

    datos["Fuente"] = datos["fuente"].astype(str)
    datos["Sentimiento"] = (
        datos["sentimiento"]
        .fillna("no_evaluado")
        .astype(str)
    )

    datos["Estado"] = np.where(
        es_verdadero(datos["es_outlier"]),
        "Outlier",
        "Normal"
    )

    datos["Evidencia textual"] = np.where(
        evidencia,
        "Candidato léxico sin validar",
        "Sin coincidencia léxica"
    )

    datos["Tamaño"] = np.where(evidencia, 12, 8)
    datos["Índice"] = datos["indice_original"].astype(int)

    def comentario_corto(texto):
        texto = " ".join(str(texto).split())

        if len(texto) > 300:
            texto = texto[:297].rstrip() + "..."

        lineas = textwrap.wrap(
            texto, width=55, break_long_words=True
        )

        return "<br>".join(
            escape(linea) for linea in lineas
        )

    datos["Comentario"] = (
        datos["texto"].fillna("")
        .astype(str)
        .apply(comentario_corto)
    )

    fuentes = sorted(datos["Fuente"].unique())
    posiciones = {fuente: i for i, fuente in enumerate(fuentes)}

    desplazamiento = (
        (datos["Índice"] * 37 % 101) / 100 - 0.5
    ) * 0.54

    datos["Posición"] = (
        datos["Fuente"].map(posiciones).astype(float)
        + desplazamiento
    )


    if paleta not in PALETAS:
        raise ValueError("Paleta no admitida")

    colores = px.colors.sample_colorscale(
        PALETAS[paleta],
        np.linspace(0.08, 0.92, max(2, len(fuentes)))
    )

    mapa_colores = {
        fuente: colores[i]
        for i, fuente in enumerate(fuentes)
    }

    partes = [
        "<!doctype html><html lang='es'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        "<title>" + escape(titulo) + "</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;"
        "max-width:1250px;margin:28px auto;padding:0 18px;"
        "color:#24323b}"
        "h1{margin-bottom:12px}"
        "section{margin:32px 0 48px}"
        ".nota{line-height:1.6;color:#53616d}"
        "details{padding:12px 16px;border:1px solid #ddd;"
        "border-radius:8px;margin-top:12px}"
        "li{margin:12px 0;line-height:1.5}"
        "</style></head><body>"
        "<h1>" + escape(titulo) + "</h1>"
        "<p class='nota'>Cada punto representa un comentario. "
        "El eje horizontal muestra su similitud coseno con "
        "un concepto económico y el eje vertical identifica "
        "su fuente. El pequeño desplazamiento vertical evita "
        "superposiciones; no representa una medida adicional. "
        "Los puntos más grandes tienen evidencia léxica, "
        "pero no están validados como opiniones económicas. "
        "Los colores distinguen fuentes y las formas indican "
        "sentimientos. No se aplicaron umbrales.</p>"
    ]

    for numero, (concepto, columna, etiqueta) in enumerate(
        CONCEPTOS
    ):
        datos["Similitud coseno"] = datos[columna]

        figura = px.scatter(
            datos,
            x="Similitud coseno",
            y="Posición",
            color="Fuente",
            symbol="Sentimiento",
            size="Tamaño",
            size_max=13,
            color_discrete_map=mapa_colores,
            symbol_map={
                "positivo": "circle",
                "negativo": "x",
                "neutral": "diamond",
                "no_evaluado": "cross"
            },
            hover_data={
                "Posición": False,
                "Tamaño": False,
                "Índice": True,
                "Comentario": True,
                "Estado": True,
                "Evidencia textual": True,
                "Similitud coseno": ":.4f"
            },
            render_mode=(
                "svg" if len(datos) <= 1500 else "webgl"
            ),
            title=etiqueta
        )

        figura.update_yaxes(
            tickvals=list(range(len(fuentes))),
            ticktext=fuentes,
            title_text="Fuente",
            range=[-0.65, len(fuentes) - 0.35]
        )

        figura.update_xaxes(
            title_text="Similitud coseno",
            zeroline=True,
            zerolinecolor="#999999"
        )

        figura.update_traces(
            marker=dict(opacity=0.78)
        )

        figura.update_layout(
            height=max(490, len(fuentes) * 95),
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="#1F2937",
                font=dict(color="white", size=12),
                align="left"
            ),
            margin=dict(l=55, r=30, t=65, b=55)
        )

        partes.append("<section><h2>" + etiqueta + "</h2>")

        partes.append(
            pio.to_html(
                figura,
                full_html=False,
                include_plotlyjs=(numero == 0)
            )
        )

        ejemplos = (
            cercanos[cercanos["concepto"] == concepto]
            .sort_values("posicion")
            .head(5)
        )

        partes.append(
            "<details><summary>"
            "Ver los cinco comentarios más cercanos"
            "</summary><ol>"
        )

        for _, fila in ejemplos.iterrows():
            texto = " ".join(str(fila["texto"]).split())

            if len(texto) > 350:
                texto = texto[:347].rstrip() + "..."

            partes.append(
                "<li><strong>"
                + escape(str(fila["fuente"]))
                + " · similitud "
                + f'{float(fila["similitud_coseno"]):.4f}'
                + "</strong><p>"
                + escape(texto)
                + "</p></li>"
            )

        partes.append("</ol></details></section>")

    partes.append(
        "<p class='nota'>Advertencia metodológica: "
        "la similitud semántica no demuestra que exista "
        "una opinión económica ni que esta sea positiva "
        "o negativa. Se requiere revisión de pertinencia."
        "</p></body></html>"
    )

    ruta = Path(ruta)
    ruta.write_text("".join(partes), encoding="utf-8")

    return {
        "documentos": len(datos),
        "conceptos": len(CONCEPTOS),
        "archivo": str(ruta)
    }
