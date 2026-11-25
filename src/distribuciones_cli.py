from pathlib import Path
from html import escape

import plotly.express as px
import plotly.io as pio
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

    for columna, encabezado in [
        ("Topico", "Distribucion de topicos"),
        ("Sentimiento", "Distribucion de sentimientos originales"),
        ("Polaridad binaria", "Distribucion de polaridad binaria")
    ]:
        figura = px.histogram(
            base,
            x="Universo",
            color=columna,
            barmode="stack",
            color_discrete_sequence=PALETAS[paleta],
            title=encabezado
        )

        figura.update_layout(
            barnorm="percent",
            yaxis_title="Porcentaje de comentarios",
            xaxis_title="Tipo de imagen"
        )

        figura.update_yaxes(range=[0, 100])
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
