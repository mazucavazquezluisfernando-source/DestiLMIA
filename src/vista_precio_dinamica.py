import pandas as pd
import plotly.graph_objects as go
import streamlit as st


CONCEPTOS = {
    "Precio y costo": "media_precio",
    "Valor de la experiencia": "media_valor",
    "Relación calidad-precio": "media_calidad_precio",
}


def preparar_precio(tablas):

    resumen = tablas["precio"].copy()
    detalle = tablas["precio_detalle"]
    cercanos = tablas["precio_cercanos"].copy()

    columnas = [
        "documentos",
        "candidatos_dinero",
        "candidatos_valor",
        *CONCEPTOS.values(),
    ]

    for columna in columnas:
        resumen[columna] = pd.to_numeric(
            resumen[columna],
            errors="raise"
        )

    cercanos["similitud_coseno"] = pd.to_numeric(
        cercanos["similitud_coseno"],
        errors="raise"
    )

    return resumen, detalle, cercanos


def render_precio_dinamica(tablas, carpeta, mostrar_mapa):

    from pathlib import Path
    from html import escape
    from plotly.colors import sample_colorscale

    from src.tema_global import (
        obtener_paleta,
        mostrar_kpis,
        mostrar_grafica
    )

    from src.vista_temas_sentimiento import leer_mapas

    resumen, detalle, cercanos = preparar_precio(tablas)

    carpeta = Path(carpeta)
    paleta = obtener_paleta(carpeta)

    color_dmo, color_usuario = sample_colorscale(
        paleta, [0.15, 0.72]
    )

    conceptos = {
        "precio_costo": "Precio y costo",
        "valor_experiencia": "Valor de la experiencia",
        "relacion_calidad_precio": "Relación calidad-precio"
    }

    etiquetas = ["Costo", "Experiencia", "Calidad-precio"]

    archivo = carpeta / "precio_valor_dmo_usuarios.csv"

    if not archivo.is_file():
        st.warning("No hay comparación económica disponible.")
        return

    grupos = pd.read_csv(archivo).set_index(
        "universo"
    ).reindex(["DMO", "Usuarios"])

    total = len(detalle)
    candidatos = int(grupos["candidatos_lexicos"].sum())

    st.markdown("## Precio y valor de la experiencia")


    mostrar_kpis([
        (
            "Textos analizados",
            f"{total:,}",
            "Incluye textos atípicos"
        ),
        (
            "Precio y costo",
            int(resumen["candidatos_dinero"].sum()),
            "Textos con evidencia léxica"
        ),
        (
            "Valor de la experiencia",
            int(resumen["candidatos_valor"].sum()),
            "Textos con evidencia léxica"
        ),
        (
            "Candidatos económicos",
            candidatos,
            f"{candidatos / total:.1%} del corpus"
            if total else "Sin textos"
        )
    ], paleta)

    izquierda, derecha = st.columns(2)


    with izquierda:
        with st.container(border=True):

            st.markdown("**Cercanía semántica por concepto**")

            figura = go.Figure()

            for universo, color, patron in [
                ("DMO", color_dmo, "/"),
                ("Usuarios", color_usuario, "")
            ]:

                valores = [
                    grupos.loc[universo, f"media_{c}"]
                    for c in conceptos
                ]

                figura.add_bar(
                    name=universo,
                    x=etiquetas,
                    y=valores,
                    marker=dict(
                        color=color,
                        pattern=dict(shape=patron)
                    ),
                    text=[
                        f"{v:.3f}" if pd.notna(v) else ""
                        for v in valores
                    ],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "%{x}<br>Similitud media: "
                        "%{y:.3f}<extra></extra>"
                    )
                )

            figura.update_layout(
                barmode="group",
                bargap=0.35
            )

            figura.update_yaxes(
                title="Similitud coseno",
                rangemode="tozero"
            )

            mostrar_grafica(figura, "economia_grupos", 220)


    with derecha:
        with st.container(border=True):

            st.markdown("**Conceptos económicos por fuente**")

            fuentes = resumen.sort_values(
                "documentos", ascending=False
            ).head(6)

            matriz = fuentes[[
                "media_precio",
                "media_valor",
                "media_calidad_precio"
            ]]

            figura = go.Figure(go.Heatmap(
                z=matriz.values,
                x=etiquetas,
                y=fuentes["fuente"].astype(str).map(escape),
                colorscale=paleta,
                texttemplate="%{z:.3f}",
                colorbar=dict(
                    title="Coseno",
                    thickness=9
                ),
                hovertemplate=(
                    "%{y}<br>%{x}: %{z:.3f}"
                    "<extra></extra>"
                )
            ))

            figura.update_yaxes(autorange="reversed")

            mostrar_grafica(figura, "economia_heatmap", 220)

            if len(resumen) > 6:
                st.caption("Seis fuentes con más textos.")

    izquierda, derecha = st.columns([1.6, 1])


    with izquierda:
        with st.container(border=True):

            st.markdown("**Mapa semántico económico**")

            archivo_mapa = carpeta / "precio_valor_scatter.html"

            mapas = (
                leer_mapas(
                    archivo_mapa,
                    archivo_mapa.stat().st_mtime_ns
                )
                if archivo_mapa.is_file() else []
            )

            if mapas:

                elegido = 0

                if len(mapas) > 1:

                    titulos = []

                    for i, (_, layout) in enumerate(mapas):

                        titulo = layout.get("title", {})

                        if isinstance(titulo, dict):
                            titulo = titulo.get("text", "")

                        titulos.append(titulo or f"Mapa {i + 1}")

                    elegido = st.selectbox(
                        "Mapa",
                        range(len(mapas)),
                        format_func=lambda i: titulos[i],
                        label_visibility="collapsed",
                        key="selector_mapa_economico"
                    )

                datos, layout = mapas[elegido]

                figura = go.Figure(
                    data=datos,
                    layout=layout
                )

                figura.update_layout(
                    title=None,
                    width=None,
                    height=320,
                    autosize=True,
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF",
                    font=dict(
                        family="Inter, Arial, sans-serif",
                        size=11,
                        color="#172334"
                    ),
                    margin=dict(l=10, r=10, t=15, b=30),
                    legend=dict(font=dict(size=10))
                )

                figura.update_xaxes(
                    gridcolor="#EDF0F4",
                    automargin=True
                )

                figura.update_yaxes(
                    gridcolor="#EDF0F4",
                    automargin=True
                )

                st.plotly_chart(
                    figura,
                    width="stretch",
                    theme=None,
                    key="scatter_economia",
                    config={"displaylogo": False}
                )

            else:

                mostrar_mapa(
                    "precio_valor_scatter.html",
                    "economia_alternativa",
                    400,
                    carpeta
                )

            st.caption(
                "Pasa el cursor sobre los puntos "
                "para consultar los comentarios."
            )


    with derecha:
        with st.container(border=True):

            st.markdown("**Hallazgos económicos**")
            st.caption("Textos con evidencia léxica")

            for universo, color in [
                ("DMO", color_dmo),
                ("Usuarios", color_usuario)
            ]:

                fila = grupos.loc[universo]
                porcentaje = fila["porcentaje_candidatos"]

                if pd.isna(porcentaje) or not fila["documentos"] > 0:
                    st.caption(f"{universo}: sin datos.")
                    continue

                st.html(f"""
                <div style="margin-bottom:8px;">
                    <div style="display:flex;
                    justify-content:space-between;">
                        <strong>{universo}</strong>
                        <strong>{porcentaje:.1f}%</strong>
                    </div>
                    <div style="font-size:12px;color:#526174;">
                        {int(fila['candidatos_lexicos'])}
                        de {int(fila['documentos'])} textos
                    </div>
                    <div style="height:8px;background:#EDF0F4;
                    border-radius:5px;">
                        <div style="height:8px;
                        width:{porcentaje:.2f}%;
                        background:{color};
                        border-radius:5px;">
                        </div>
                    </div>
                </div>
                """)

            st.markdown("**Tono de los textos candidatos**")

            clases = [
                ("Positivo", "positivo", "/"),
                ("Neutral", "neutral", ""),
                ("Negativo", "negativo", "x"),
                ("Sin evaluar", "no_evaluado", ".")
            ]

            colores = sample_colorscale(
                paleta, [0.72, 0.40, 0.10, 0.90]
            )

            figura = go.Figure()

            totales = grupos["candidatos_lexicos"].replace(
                0, float("nan")
            )

            for (nombre, campo, patron), color in zip(
                clases, colores
            ):

                cantidades = grupos[campo]
                porcentajes = cantidades.div(totales).mul(100)

                figura.add_bar(
                    name=nombre,
                    x=porcentajes,
                    y=grupos.index.tolist(),
                    orientation="h",
                    marker=dict(
                        color=color,
                        pattern=dict(shape=patron)
                    ),
                    customdata=cantidades,
                    hovertemplate=(
                        "%{y}<br>%{x:.1f}%"
                        "<br>%{customdata} textos"
                        "<extra></extra>"
                    )
                )

            figura.update_layout(
                barmode="stack",
                bargap=0.4
            )

            figura.update_xaxes(
                range=[0, 100],
                ticksuffix="%",
                dtick=50
            )

            figura.update_yaxes(autorange="reversed")

            mostrar_grafica(figura, "economia_tono", 160)

            st.caption(
                "El sentimiento se estima con hasta 512 tokens; no es específico del precio."
            )


    @st.dialog("Explorar comentarios económicos", width="large")
    def explorar():

        concepto = st.selectbox(
            "Concepto",
            list(conceptos),
            format_func=lambda c: conceptos[c]
        )

        universo = st.radio(
            "Origen",
            ["Todos", "DMO", "Usuarios"],
            horizontal=True
        )

        if universo == "Todos":

            seleccion = cercanos[
                cercanos["concepto"].eq(concepto)
            ].copy()

        else:

            archivo = carpeta / "precio_valor_contexto_universos.csv"

            if not archivo.is_file():
                st.info("No hay comentarios por universo.")
                return

            contexto = pd.read_csv(
                archivo,
                dtype={"fuente": str, "texto": str, "frase_mas_cercana": str},
                keep_default_na=False
            )

            seleccion = contexto[
                contexto["concepto"].eq(concepto)
                & contexto["universo"].eq(universo)
            ].copy()

        seleccion["similitud_coseno"] = pd.to_numeric(
            seleccion["similitud_coseno"], errors="coerce"
        )

        seleccion = seleccion.dropna(
            subset=["similitud_coseno"]
        ).sort_values(
            "similitud_coseno", ascending=False
        ).head(5).reset_index(drop=True)

        st.caption(
            "Hasta cinco comentarios con mayor similitud "
            "semántica al concepto."
        )

        if seleccion.empty:

            st.info("No hay comentarios disponibles.")

        else:

            indice = st.selectbox(
                "Publicación",
                seleccion.index.tolist(),
                format_func=lambda i: (
                    f"{i + 1}. "
                    f"{seleccion.loc[i, 'fuente']} · "
                    f"{seleccion.loc[i, 'similitud_coseno']:.3f}"
                )
            )

            fila = seleccion.loc[indice]

            a, b = st.columns(2)

            a.metric(
                "Similitud coseno",
                f"{fila['similitud_coseno']:.3f}"
            )

            b.metric(
                "Sentimiento",
                str(fila["sentimiento"]).capitalize()
            )

            st.caption(f"Fuente: {fila['fuente']}")

            st.html(f"""
            <div style="background:#F5F7FA;
            border-left:4px solid {color_dmo};
            padding:14px;border-radius:8px;
            overflow-wrap:anywhere;white-space:pre-wrap;">
                {escape(str(fila["texto"]))}
            </div>
            """)

            for campo, nombre in [
                ("evidencia_lexica", "Evidencia léxica"),
                ("evidencia_dinero", "Evidencia de dinero"),
                ("evidencia_valor", "Evidencia de valor")
            ]:

                if campo in fila.index:

                    valor = fila[campo]

                    evidencia = (
                        "No disponible" if pd.isna(valor) or valor == ""
                        else "Sí" if str(valor).lower()
                        in ("true", "1", "1.0", "sí")
                        else "No"
                    )

                    st.caption(f"{nombre}: {evidencia}")

            if "frase_mas_cercana" in fila.index:
                st.caption(
                    "Referencia: " + str(fila["frase_mas_cercana"])
                )

            st.dataframe(
                seleccion[[
                    "fuente",
                    "sentimiento",
                    "similitud_coseno"
                ]].rename(columns={
                    "fuente": "Fuente",
                    "sentimiento": "Sentimiento",
                    "similitud_coseno": "Similitud"
                }).round(3),
                hide_index=True,
                width="stretch"
            )

        with st.expander("Consultar métricas completas"):

            st.dataframe(
                resumen.round(3),
                hide_index=True,
                width="stretch"
            )

            st.dataframe(
                grupos.reset_index().round(3),
                hide_index=True,
                width="stretch"
            )

            st.caption(
                "El percentil 90 es un criterio relativo "
                "al corpus, no un umbral validado de relevancia."
            )

            if archivo_mapa.is_file():

                st.download_button(
                    "Descargar mapa interactivo",
                    data=archivo_mapa.read_bytes(),
                    file_name=archivo_mapa.name,
                    mime="text/html"
                )

    izquierda, derecha = st.columns([3, 1.4])

    with izquierda:

        st.caption(
            "Las señales económicas requieren revisión contextual. "
            "La similitud no equivale a satisfacción."
        )

    with derecha:

        if st.button(
            "Explorar comentarios económicos",
            width="stretch",
            key="explorar_economia"
        ):
            explorar()
