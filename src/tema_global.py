from html import escape
from pathlib import Path
import json

from plotly.colors import sample_colorscale
import streamlit as st


PALETAS = {
    "viridis": "Viridis",
    "cividis": "Cividis",
    "plasma": "Plasma",
    "inferno": "Inferno"
}


def aplicar_tema():

    st.html("""
    <style>

    :root {
        --dest-fondo: #FFFFFF;
        --dest-texto: #172334;
        --dest-secundario: #526174;
        --dest-borde: #E1E6ED;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"],
    [data-testid="stSidebar"] {
        background: #FFFFFF !important;
        color: #172334;
    }

    [data-testid="stMainBlockContainer"] {
        padding: 3.2rem 1.6rem 1rem !important;
        max-width: 100% !important;
    }

    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp p,
    .stApp label,
    .stApp button,
    [data-testid="stMetric"],
    .dest-barra,
    .dest-kpi-grid {
        font-family: Inter, -apple-system,
                     BlinkMacSystemFont, sans-serif !important;
    }

    [data-testid="stMainBlockContainer"]
    [data-testid="stVerticalBlock"] {
        gap: 0.65rem;
    }

    [data-testid="stMainBlockContainer"] h1 {
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.035em;
    }

    [data-testid="stMainBlockContainer"] h2 {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMainBlockContainer"] h3 {
        font-size: 1.05rem !important;
        font-weight: 650 !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #E1E6ED !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 6px rgba(23,35,52,.035);
    }

    [data-testid="stMetric"] {
        padding: 10px 14px !important;
        background: #FFFFFF !important;
        border: 1px solid #E1E6ED !important;
        border-radius: 12px !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        color: #172334 !important;
        font-weight: 700 !important;
    }

    [data-testid="stSegmentedControl"]
    button[data-testid$="Primary"],
    [data-testid="stSegmentedControl"]
    button[aria-pressed="true"],
    [data-testid="stSegmentedControl"]
    button[aria-checked="true"] {
        background: #2A788E !important;
        color: white !important;
        border-color: #2A788E !important;
    }

    .dest-barra {
        border-color: #E1E6ED !important;
        padding: 10px 16px !important;
        border-radius: 12px !important;
    }

    .dest-marca {
        color: #172334 !important;
    }

    .dest-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 5px;
    }

    .dest-kpi {
        border: 1px solid #E1E6ED;
        border-radius: 12px;
        padding: 10px 14px;
        min-width: 0;
        background: #FFFFFF;
    }

    .dest-kpi-label {
        font-size: 12px;
        font-weight: 600;
        color: #526174;
    }

    .dest-kpi-value {
        font-size: 28px;
        line-height: 1.25;
        letter-spacing: -0.035em;
        font-weight: 700;
        color: #172334;
        overflow-wrap: anywhere;
    }

    .dest-kpi-detail {
        font-size: 11px;
        color: #526174;
    }

    button:focus-visible,
    a:focus-visible {
        outline: 2px solid #2A788E !important;
        outline-offset: 2px;
    }

    @media (max-width: 850px) {
        .dest-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    </style>
    """)


def leer_meta(carpeta):

    return json.loads(
        (Path(carpeta) / "metadatos_analisis.json")
        .read_text(encoding="utf-8")
    )


def obtener_paleta(carpeta):

    nombre = leer_meta(carpeta).get("paleta", "viridis")

    return PALETAS.get(nombre, "Viridis")


def colores_paleta(paleta, cantidad):

    if cantidad <= 0:
        return []

    if cantidad == 1:
        posiciones = [0.40]
    else:
        posiciones = [
            0.10 + 0.72 * i / (cantidad - 1)
            for i in range(cantidad)
        ]

    return sample_colorscale(paleta, posiciones)


def colores_sentimiento(paleta):

    negativo, neutral, positivo = sample_colorscale(
        paleta, [0.10, 0.40, 0.72]
    )

    return {
        "Positivo": positivo,
        "Neutral": neutral,
        "Negativo": negativo
    }


def mostrar_kpis(indicadores, paleta):

    colores = colores_paleta(
        paleta, len(indicadores)
    )

    contenido = '<div class="dest-kpi-grid">'

    for (titulo, valor, detalle), color in zip(
        indicadores, colores
    ):

        contenido += f"""
        <div class="dest-kpi"
             style="border-top:3px solid {color}">
            <div class="dest-kpi-label">
                {escape(str(titulo))}
            </div>
            <div class="dest-kpi-value">
                {escape(str(valor))}
            </div>
            <div class="dest-kpi-detail">
                {escape(str(detalle))}
            </div>
        </div>
        """

    st.html(contenido + "</div>")


def mostrar_grafica(figura, clave, altura=230):

    figura.update_layout(
        height=altura,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Inter, Arial, sans-serif",
            color="#172334",
            size=11
        ),
        margin=dict(l=10, r=20, t=25, b=25),
        legend=dict(
            orientation="h",
            x=0,
            y=1.13,
            font=dict(size=10),
            title=None
        )
    )

    figura.update_xaxes(
        gridcolor="#EEF1F5",
        zerolinecolor="#D8E0E8",
        automargin=True
    )

    figura.update_yaxes(
        automargin=True,
        gridcolor="#EEF1F5"
    )

    st.plotly_chart(
        figura,
        width="stretch",
        theme=None,
        key=clave,
        config={
            "displaylogo": False,
            "responsive": True
        }
    )
