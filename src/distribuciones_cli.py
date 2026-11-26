from pathlib import Path
from html import escape

import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from src.scatter_comentarios_cli import PALETAS


def generar_distribuciones(
    datos, columna_fuente, etiqueta_dmo, ruta, titulo, paleta
):

    if paleta not in PALETAS:
        raise ValueError("Paleta no admitida")

    necesarias = {columna_fuente, "topico", "sentimiento", "polaridad_binaria"}

    if not necesarias.issubset(datos.columns):
        raise ValueError("Faltan columnas para las distribuciones")

    base = datos.copy()

    if base.empty:
        raise ValueError("No hay documentos normales")

    base["Universo"] = base[columna_fuente].astype(str).eq(
        str(etiqueta_dmo)
    ).map({True: "DMO", False: "Usuarios"})

    base["Topico"] = base["topico"].map(
        lambda x: f"Topico {int(x)}" if x >= 0 else "Sin tópico (muestra pequeña)"
    )

    base["Sentimiento"] = base["sentimiento"].astype(str)
    base["Polaridad binaria"] = base["polaridad_binaria"].astype(str)

    figuras = []

    colores_sentimiento = dict(zip(
        ["negativo", "neutral", "positivo"],
        px.colors.sample_colorscale(
            PALETAS[paleta], [0.10, 0.40, 0.72]
        )
    ))

    for columna, encabezado in [
        ("Topico", "Distribución de tópicos"),
        ("Sentimiento", "Distribución de sentimientos originales"),
        ("Polaridad binaria", "Distribución de polaridad binaria")
    ]:

        if columna == "Topico":
            categorias = sorted(
                base[columna].unique(),
                key=lambda nombre: (
                    not nombre.startswith("Topico "),
                    int(nombre.split()[-1])
                    if nombre.startswith("Topico ") else 0
                )
            )

            cantidad = len(categorias)

            posiciones = [
                0.10 + 0.72 * i / (cantidad - 1)
                for i in range(cantidad)
            ] if cantidad > 1 else [0.40]

            colores = dict(zip(
                categorias,
                px.colors.sample_colorscale(
                    PALETAS[paleta], posiciones
                )
            ))

        else:
            categorias = (
                ["negativo", "neutral", "positivo"]
                if columna == "Sentimiento"
                else ["negativo", "positivo"]
            )

            colores = colores_sentimiento

        if not set(base[columna]).issubset(categorias):
            raise ValueError("Categorías no reconocidas")

        conteos = (
            base.groupby(["Universo", columna])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=categorias, fill_value=0)
        )

        universos = [
            grupo for grupo in ["DMO", "Usuarios"]
            if grupo in conteos.index
        ]

        conteos = conteos.loc[universos]
        porcentajes = conteos.div(conteos.sum(axis=1), axis=0) * 100

        figura = go.Figure()

        for categoria in categorias:
            valores = porcentajes[categoria].tolist()

            figura.add_bar(
                name=categoria,
                x=universos,
                y=valores,
                customdata=conteos[categoria].tolist(),
                marker=dict(color=colores[categoria]),
                text=[
                    f"{valor:.1f}%" if valor >= 6 else ""
                    for valor in valores
                ],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate=(
                    "%{x}<br>"
                    "%{y:.1f}%<br>"
                    "%{customdata} documentos"
                    "<extra>%{fullData.name}</extra>"
                )
            )

        figura.update_layout(
            title=encabezado,
            barmode="stack",
            yaxis_title="Porcentaje de comentarios",
            xaxis_title="Grupo analizado",
            legend_title_text=columna,
            uniformtext_minsize=10,
            uniformtext_mode="hide"
        )

        figura.update_yaxes(range=[0, 100], ticksuffix="%")
        figuras.append(figura)

    pagina = (
        "<!doctype html><html lang='es'><head>"
        "<meta charset='utf-8'></head><body>"
        "<h1>" + escape(titulo) + "</h1>"
        "<p>Comparacion porcentual de documentos normales.</p>"
        + pio.to_html(
            figuras[0], full_html=False, include_plotlyjs=True
        )
        + pio.to_html(
            figuras[1], full_html=False, include_plotlyjs=False
        )
        + pio.to_html(figuras[2], full_html=False, include_plotlyjs=False)
        + "<p>El sentimiento incluye la clase neutral original. "
        "Las tendencias binarias derivadas de neutrales "
        "requieren interpretacion cautelosa.</p>"
        "</body></html>"
    )

    ruta = Path(ruta)
    ruta.write_text(pagina, encoding="utf-8")

    return {"documentos": len(base), "archivo": str(ruta)}
