from datetime import datetime
from html import escape
from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def obtener_fecha(carpeta):
    metadatos = Path(carpeta) / "metadatos_analisis.json"

    if metadatos.exists():
        try:
            datos = json.loads(
                metadatos.read_text(encoding="utf-8")
            )
            if datos.get("estado") == "finalizado":
                fecha = datetime.fromisoformat(
                    datos["fecha_analisis"]
                )
                return fecha.strftime("%d/%m/%Y"), "Fecha del análisis"
        except (ValueError, KeyError, TypeError):
            pass

    return "No registrada", "Fecha del análisis"


def nombre_analisis(carpeta):

    ruta = Path(carpeta) / "metadatos_analisis.json"

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        titulo = str(datos.get("titulo") or "").strip()
        return titulo or "Análisis sin título"
    except (OSError, ValueError, TypeError):
        return "Análisis sin título"


def render_barra_control(carpeta):
    if carpeta is None:
        st.warning("No hay un análisis completo disponible.")
        return

    fecha, etiqueta = obtener_fecha(carpeta)
    titulo_seguro = escape(nombre_analisis(carpeta))
    st.html("""
    <style>
    .dest-barra {
        background: #FFFFFF;
        border: 1px solid #DDD7CC;
        border-radius: 16px;
        padding: 10px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 4px;
    }
    .dest-marca {
        font-size: 27px;
        font-weight: 800;
        color: #63394F;
    }
    .dest-subtitulo {
        font-size: 12px;
        color: #595B52;
    }
    .dest-titulo {
        font-size: 18px;
        font-weight: 700;
        line-height: 1.4;
        color: #282821;
        margin-top: 2px;
        overflow-wrap: anywhere;
    }

    .dest-fecha {
        text-align: right;
        font-size: 18px;
        font-weight: 700;
        color: #282821;
    }
    .dest-fecha small {
        display: block;
        font-size: 11px;
        color: #595B52;
    }
    </style>
    """)

    st.html(f"""
    <div class="dest-barra">
        <div style="flex:2;min-width:220px;">
            <div class="dest-subtitulo">
                Análisis de imagen turística · DMO frente a usuarios
            </div>
            <div class="dest-titulo">{titulo_seguro}</div>
        </div>
        <div class="dest-fecha">
            <small>{escape(etiqueta)}</small>
            {escape(fecha)}
        </div>
        <div class="dest-marca">
            DestiLMIA
        </div>
    </div>
    """)


def render_panel_control(tablas, carpeta):

    from plotly.colors import sample_colorscale

    from src.tema_global import (
        leer_meta,
        obtener_paleta,
        mostrar_kpis,
        mostrar_grafica
    )

    from src.vista_temas_sentimiento import etiquetas_tematicas

    entrada = tablas["entrada"]
    topicos = tablas["topicos"].copy()
    sentimientos = tablas["sentimientos"].copy()
    alineacion = tablas["alineacion"].copy()
    outliers = tablas["outliers"]

    meta = leer_meta(carpeta)
    paleta = obtener_paleta(carpeta)

    fuente_dmo = str(meta["etiqueta_dmo"])

    colores = sample_colorscale(
        paleta, [0.10, 0.40, 0.72]
    )

    negativo, neutral, positivo = colores

    fuente = "fuente_entrada"

    total = len(entrada)
    atipicos = len(outliers)
    normales = total - atipicos

    composicion = entrada[fuente].astype(str).value_counts()

    sentimientos["Universo"] = sentimientos[fuente].astype(
        str
    ).map(
        lambda f: "DMO" if f == fuente_dmo else "Usuarios"
    )

    campos = ["documentos", "positivos", "neutrales", "negativos"]

    grupos = sentimientos.groupby("Universo")[campos].sum()

    evaluados = int(grupos["documentos"].sum())


    alineacion["alineacion_coseno"] = pd.to_numeric(
        alineacion["alineacion_coseno"],
        errors="coerce"
    )

    globales = alineacion.loc[
        alineacion["tipo"].eq("global"),
        "alineacion_coseno"
    ].dropna()

    similitud = globales.iloc[0] if not globales.empty else None

    fuentes = alineacion[
        alineacion["tipo"].eq("por_fuente")
    ].dropna(
        subset=["alineacion_coseno"]
    ).sort_values(
        "alineacion_coseno",
        ascending=False
    )


    topicos["topico"] = pd.to_numeric(
        topicos["topico"], errors="coerce"
    )

    temas = topicos[topicos["topico"] >= 0].copy()

    temas["Universo"] = temas[fuente].astype(str).map(
        lambda f: "DMO" if f == fuente_dmo else "Usuarios"
    )

    presencia = pd.crosstab(
        temas["topico"],
        temas["Universo"]
    ).reindex(
        columns=["DMO", "Usuarios"],
        fill_value=0
    )

    compartidos = int(
        (
            (presencia["DMO"] > 0)
            & (presencia["Usuarios"] > 0)
        ).sum()
    )

    solo_dmo = int(
        (
            (presencia["DMO"] > 0)
            & (presencia["Usuarios"] == 0)
        ).sum()
    )

    solo_usuarios = int(
        (
            (presencia["DMO"] == 0)
            & (presencia["Usuarios"] > 0)
        ).sum()
    )

    nombres = etiquetas_tematicas(temas, "topico")


    archivo = carpeta / "precio_valor_dmo_usuarios.csv"

    candidatos = None
    porcentaje_usuarios = None

    if archivo.is_file():

        economia = pd.read_csv(archivo)

        candidatos = int(
            economia["candidatos_lexicos"].sum()
        )

        usuarios = economia[
            economia["universo"].eq("Usuarios")
        ]

        if not usuarios.empty:

            valor = usuarios.iloc[0]["porcentaje_candidatos"]

            if pd.notna(valor):
                porcentaje_usuarios = float(valor)

    st.markdown("## Panorama de la imagen del destino")

    st.caption(
        "Resumen ejecutivo de la comunicación oficial "
        "y la percepción digital."
    )


    mostrar_kpis([
        (
            "Corpus analizado",
            f"{total:,}",
            f"{len(composicion)} fuentes digitales"
        ),
        (
            "Alineación DMO · usuarios",
            f"{similitud:.3f}"
            if similitud is not None else "No calculable",
            "Similitud semántica"
        ),
        (
            "Temas compartidos",
            f"{compartidos} de {len(presencia)}",
            f"{solo_dmo} solo DMO · {solo_usuarios} solo usuarios"
        ),
        (
            "Señales económicas",
            f"{candidatos / total:.1%}"
            if candidatos is not None and total
            else "No disponible",
            f"{candidatos:,} textos candidatos"
            if candidatos is not None
            else "Sin indicadores económicos"
        )
    ], paleta)

    a, b, c = st.columns(3)


    with a:
        with st.container(border=True):

            st.markdown("**Composición del corpus**")

            if total:

                vista = composicion.head(5).copy()

                if len(composicion) > 5:

                    etiqueta = "Otras fuentes"

                    while etiqueta in composicion.index:
                        etiqueta += " (agrupadas)"

                    vista.loc[etiqueta] = int(
                        composicion.iloc[5:].sum()
                    )

                colores_fuentes = sample_colorscale(
                    paleta,
                    [
                        0.10 + i * 0.78 / max(1, len(vista)-1)
                        for i in range(len(vista))
                    ]
                )

                figura = go.Figure(go.Pie(
                    labels=[
                        escape(str(f)) for f in vista.index
                    ],
                    values=vista.values,
                    hole=0.67,
                    sort=False,
                    marker=dict(
                        colors=colores_fuentes,
                        line=dict(
                            color="#FFFFFF",
                            width=2
                        )
                    ),
                    textinfo="percent",
                    textposition="inside",
                    showlegend=True,
                    hovertemplate=(
                        "%{label}<br>%{value:,} textos"
                        "<br>%{percent}<extra></extra>"
                    )
                ))

                figura.add_annotation(
                    x=0.5,
                    y=0.5,
                    text=f"<b>{total:,}</b><br>textos",
                    showarrow=False,
                    font=dict(size=19)
                )

                mostrar_grafica(
                    figura,
                    "panorama_composicion",
                    245
                )

                cantidad_dmo = int(
                    composicion.get(fuente_dmo, 0)
                )

                st.caption(
                    f"DMO: {cantidad_dmo:,} · "
                    f"Usuarios: {total-cantidad_dmo:,} textos"
                )

            else:
                st.info("No hay textos disponibles.")


    with b:
        with st.container(border=True):

            st.markdown("**Sentimiento: DMO vs usuarios**")

            if evaluados:

                figura = go.Figure()

                denominador = grupos["documentos"].replace(
                    0, float("nan")
                )

                for nombre, campo, color, patron in [
                    ("Positivo", "positivos", positivo, "/"),
                    ("Neutral", "neutrales", neutral, ""),
                    ("Negativo", "negativos", negativo, "x")
                ]:

                    valores = grupos[campo].div(
                        denominador
                    ).mul(100)

                    figura.add_bar(
                        name=nombre,
                        x=valores,
                        y=grupos.index.tolist(),
                        orientation="h",
                        marker=dict(
                            color=color,
                            pattern=dict(shape=patron)
                        ),
                        customdata=grupos[campo],
                        text=[
                            f"{v:.0f}%" if v >= 12 else ""
                            for v in valores
                        ],
                        textposition="inside",
                        hovertemplate=(
                            "%{y}<br>" + nombre +
                            ": %{x:.1f}%"
                            "<br>%{customdata} textos"
                            "<extra></extra>"
                        )
                    )

                figura.update_layout(
                    barmode="stack",
                    bargap=0.45
                )

                figura.update_xaxes(
                    range=[0, 100],
                    ticksuffix="%",
                    dtick=25
                )

                figura.update_yaxes(
                    autorange="reversed",
                    showgrid=False
                )

                mostrar_grafica(
                    figura,
                    "panorama_sentimiento",
                    245
                )

                if "DMO" in grupos.index:

                    fila = grupos.loc["DMO"]

                    if fila["documentos"] > 0:

                        porcentaje = (
                            fila["neutrales"]
                            / fila["documentos"] * 100
                        )

                        st.caption(
                            f"El {porcentaje:.1f}% de los textos "
                            "de la DMO son neutrales."
                        )

            else:
                st.info("No hay sentimiento evaluado.")


    with c:
        with st.container(border=True):

            st.markdown("**Alineación con la DMO**")

            if not fuentes.empty:

                vista = fuentes.head(5)

                if len(fuentes) > 5:
                    vista = pd.concat([
                        fuentes.head(4),
                        fuentes.tail(1)
                    ])

                etiquetas = [
                    escape(str(f))
                    for f in vista["fuente_percibida"]
                ]

                lineas_x = []
                lineas_y = []

                for nombre, valor in zip(
                    etiquetas, vista["alineacion_coseno"]
                ):

                    lineas_x.extend([0, valor, None])
                    lineas_y.extend([nombre, nombre, None])

                figura = go.Figure()

                figura.add_scatter(
                    x=lineas_x,
                    y=lineas_y,
                    mode="lines",
                    line=dict(
                        color="#BFCBD7",
                        width=3
                    ),
                    showlegend=False,
                    hoverinfo="skip"
                )

                figura.add_scatter(
                    x=vista["alineacion_coseno"],
                    y=etiquetas,
                    mode="markers+text",
                    marker=dict(
                        size=10,
                        color=positivo
                    ),
                    text=[
                        f"{v:.3f}"
                        for v in vista["alineacion_coseno"]
                    ],
                    textposition=[
                        "middle left" if v > 0.8
                        else "middle right"
                        for v in vista["alineacion_coseno"]
                    ],
                    showlegend=False,
                    cliponaxis=False,
                    customdata=vista["documentos_percibidos"],
                    hovertemplate=(
                        "%{y}<br>Similitud: %{x:.3f}"
                        "<br>%{customdata} textos"
                        "<extra></extra>"
                    )
                )

                limite = (
                    -1 if vista["alineacion_coseno"].min() < 0
                    else 0
                )

                figura.update_xaxes(
                    range=[limite, 1],
                    title="Similitud coseno"
                )

                figura.update_yaxes(
                    autorange="reversed",
                    showgrid=False
                )

                mostrar_grafica(
                    figura,
                    "panorama_alineacion",
                    245
                )

                mayor = fuentes["alineacion_coseno"].max()

                mejores = fuentes.loc[
                    fuentes["alineacion_coseno"].eq(mayor),
                    "fuente_percibida"
                ].astype(str).tolist()

                st.caption(
                    "Mayor alineación: "
                    + ", ".join(mejores)
                    + f" ({mayor:.3f})."
                )

                if len(fuentes) > 5:
                    st.caption(
                        "Cuatro fuentes más cercanas "
                        "y la más distante."
                    )

            else:
                st.info("No hay alineaciones calculables.")


    def ir_a(seccion):
        st.session_state["navegacion_ejecutiva"] = seccion

    st.markdown("### Principales hallazgos del análisis")

    a, b, c = st.columns(3)


    with a:
        with st.container(border=True):

            st.markdown("**Brecha temática**")

            archivo = (
                carpeta
                / "presencia_tematica_dmo_usuarios.csv"
            )

            disponible = False

            if archivo.is_file():

                brechas = pd.read_csv(archivo)

                diferencias = pd.to_numeric(
                    brechas["diferencia_pp_usuarios_menos_dmo"],
                    errors="coerce"
                ).dropna()

                if (
                    not diferencias.empty
                    and brechas["documentos_dmo"].sum() > 0
                    and brechas["documentos_usuarios"].sum() > 0
                ):

                    indice = diferencias.abs().idxmax()
                    diferencia = diferencias.loc[indice]

                    tema = int(brechas.loc[indice, "comunidad"])

                    nombre = nombres.get(
                        tema,
                        f"Tema {tema}"
                    )

                    direccion = (
                        "Mayor presencia entre usuarios."
                        if diferencia > 0
                        else "Mayor presencia en la DMO."
                        if diferencia < 0
                        else "Sin diferencia proporcional."
                    )

                    st.metric(
                        "Mayor diferencia",
                        f"{abs(diferencia):.1f} pp"
                    )

                    st.write(nombre)
                    st.caption(direccion)

                    disponible = True

            if not disponible:

                st.metric("Mayor diferencia", "No disponible")
                st.caption("Sin comparación temática suficiente.")

            st.button(
                "Consultar DMO vs usuarios",
                on_click=ir_a,
                args=("DMO vs usuarios",),
                key="panorama_ir_dmo",
                width="stretch"
            )


    with b:
        with st.container(border=True):

            st.markdown("**Precio y valor**")

            st.metric(
                "Textos de usuarios candidatos",
                f"{porcentaje_usuarios:.1f}%"
                if porcentaje_usuarios is not None
                else "No disponible"
            )

            st.write("Señales económicas")

            st.caption(
                "Evidencia léxica de precio o valor. "
                "Requiere revisión contextual."
            )

            st.button(
                "Consultar Precio y valor",
                on_click=ir_a,
                args=("Precio y valor",),
                key="panorama_ir_precio",
                width="stretch"
            )


    with c:
        with st.container(border=True):

            st.markdown("**Detección de atípicos**")

            st.metric(
                "Textos no marcados como atípicos",
                f"{normales:,} de {total:,}"
            )

            porcentaje = normales / total * 100 if total else 0

            st.html(f"""
            <div style="height:9px;display:flex;
                        border-radius:6px;overflow:hidden;
                        background:#EDF0F4;">
                <div style="width:{porcentaje:.3f}%;
                            background:{positivo};"></div>
                <div style="width:{100-porcentaje:.3f}%;
                            background:{negativo};"></div>
            </div>
            """)

            st.caption(
                f"{atipicos:,} textos marcados como atípicos."
            )

            st.button(
                "Consultar Atípicos",
                on_click=ir_a,
                args=("Atípicos",),
                key="panorama_ir_atipicos",
                width="stretch"
            )

    st.caption(
        f"Resultados exploratorios · Clasificación automática · "
        f"{evaluados:,} textos evaluados en sentimiento."
    )
