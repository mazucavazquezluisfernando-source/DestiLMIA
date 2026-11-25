import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def preparar_outliers(tablas):

    entrada = tablas["entrada"]
    outliers = tablas["outliers"].copy()
    ngramas = tablas["ngramas_outliers"].copy()

    candidatas = [
        columna
        for columna in tablas["sentimientos"].columns
        if columna in entrada.columns
        and columna in outliers.columns
    ]

    if "fuente_entrada" in candidatas:
        candidatas = ["fuente_entrada"]

    if len(candidatas) != 1:
        raise ValueError(
            "No se pudo identificar la columna de fuentes."
        )

    fuente = candidatas[0]

    textos = [
        columna
        for columna in entrada.columns
        if columna in outliers.columns
        and columna not in [fuente, "texto_limpio", "texto_lexico"]
    ]

    if "texto_entrada" in textos:
        textos = ["texto_entrada"]

    if len(textos) != 1:
        raise ValueError(
            "No se pudo identificar la columna de texto."
        )

    columna_texto = textos[0]

    if "es_outlier" in outliers.columns:
        mascara = (
            outliers["es_outlier"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "si", "sí"])
        )

        outliers = outliers[mascara].copy()

    if "frecuencia" in ngramas.columns:
        ngramas["frecuencia"] = pd.to_numeric(
            ngramas["frecuencia"],
            errors="coerce"
        )

    return entrada, outliers, ngramas, fuente, columna_texto


def render_outliers_dinamica(tablas, carpeta):

    from html import escape
    from plotly.colors import sample_colorscale

    from src.tema_global import (
        obtener_paleta,
        mostrar_kpis,
        mostrar_grafica
    )

    from src.ngramas_outliers import analizar_ngramas

    entrada, outliers, guardados, fuente, texto = preparar_outliers(tablas)

    paleta = obtener_paleta(carpeta)
    meta = tablas["metadatos"]

    colores = sample_colorscale(
        paleta, [0.15, 0.45, 0.65]
    )

    total = len(entrada)
    cantidad = len(outliers)
    porcentaje = cantidad / total * 100 if total else 0

    fuentes = entrada[fuente].astype(str).value_counts()
    anomalos = outliers[fuente].astype(str).value_counts()

    distribucion = pd.DataFrame({
        "Total": fuentes,
        "Atípicos": anomalos.reindex(
            fuentes.index, fill_value=0
        )
    })

    distribucion["Porcentaje"] = (
        distribucion["Atípicos"]
        / distribucion["Total"] * 100
    )

    distribucion = distribucion.sort_values(
        ["Porcentaje", "Atípicos"],
        ascending=False
    )

    evaluados = meta.get("outliers_evaluados") is not False

    metodo = meta.get("metodo_outliers", "isolation_forest")

    nombre_metodo = {
        "vecinos_coseno_mad": "Vecinos semánticos + MAD",
        "isolation_forest": "Isolation Forest",
        "no_evaluado": "No evaluado"
    }.get(metodo, "Método no identificado")

    st.markdown("## Textos atípicos y calidad de datos")


    mostrar_kpis([
        (
            "Textos analizados",
            f"{total:,}",
            "Corpus completo"
        ),
        (
            "Textos atípicos",
            f"{cantidad:,}" if evaluados else "No evaluado",
            nombre_metodo if evaluados else "No evaluado"
        ),
        (
            "Proporción atípica",
            f"{porcentaje:.1f}%" if evaluados else "No evaluada",
            "Del corpus completo"
        ),
        (
            "Fuentes con atípicos",
            f"{len(anomalos)} / {len(fuentes)}"
            if evaluados else "No evaluadas",
            "Fuentes del corpus"
        )
    ], paleta)

    if not evaluados:
        st.info("No hay suficientes textos para evaluar anomalías.")
        return

    if metodo == "vecinos_coseno_mad":

        umbral = meta.get("umbral_outliers")
        vecinos = meta.get("vecinos_outliers")

        if umbral is not None:
            st.caption(
                f"Vecinos: {vecinos} · Umbral: {umbral:.4f}. "
                "Puntuación = similitud promedio menos umbral."
            )

        st.caption(
            "El aislamiento semántico no implica "
            "necesariamente irrelevancia turística."
        )

    elif metodo == "isolation_forest":

        st.caption(
            "Ejecución histórica con Isolation Forest. "
            "Las puntuaciones negativas identifican atípicos."
        )

    if outliers.empty:
        st.success("No se detectaron textos atípicos.")
        return

    izquierda, derecha = st.columns(2)


    with izquierda:
        with st.container(border=True):

            st.markdown("**Proporción de atípicos por fuente**")

            vista = distribucion.head(6)

            figura = go.Figure()

            lineas_x = []
            lineas_y = []

            for nombre, fila in vista.iterrows():

                etiqueta = escape(str(nombre))

                lineas_x.extend([
                    0, fila["Porcentaje"], None
                ])

                lineas_y.extend([
                    etiqueta, etiqueta, None
                ])

            figura.add_scatter(
                x=lineas_x,
                y=lineas_y,
                mode="lines",
                line=dict(
                    color="#BFCBD7",
                    width=3
                ),
                hoverinfo="skip",
                showlegend=False
            )

            figura.add_scatter(
                x=vista["Porcentaje"],
                y=[escape(str(f)) for f in vista.index],
                mode="markers+text",
                marker=dict(
                    size=10,
                    color=colores[1]
                ),
                text=[
                    f"{int(a)}/{int(t)}"
                    for a, t in zip(
                        vista["Atípicos"],
                        vista["Total"]
                    )
                ],
                textposition="middle right",
                cliponaxis=False,
                customdata=vista[["Atípicos", "Total"]].values,
                hovertemplate=(
                    "%{y}<br>Atípicos: %{customdata[0]}"
                    "<br>Total: %{customdata[1]}"
                    "<br>Proporción: %{x:.1f}%"
                    "<extra></extra>"
                ),
                showlegend=False
            )

            limite = max(
                1, float(vista["Porcentaje"].max()) * 1.25
            )

            figura.update_xaxes(
                range=[0, min(limite, 125)],
                ticksuffix="%",
                title="Proporción dentro de cada fuente"
            )

            figura.update_yaxes(
                autorange="reversed",
                showgrid=False
            )

            mostrar_grafica(
                figura,
                "atipicos_fuentes",
                205
            )

            st.caption(
                "Cantidad de atípicos / total de la fuente."
            )

            if len(distribucion) > 6:
                st.caption("Se muestran las seis mayores proporciones.")


    with derecha:
        with st.container(border=True):

            st.markdown("**Puntuaciones de anomalía**")

            if "puntuacion_anomalia" not in outliers.columns:

                st.info("No hay puntuaciones registradas.")

            else:

                datos = outliers.copy()

                datos["puntuacion_anomalia"] = pd.to_numeric(
                    datos["puntuacion_anomalia"],
                    errors="coerce"
                )

                datos = datos.dropna(
                    subset=["puntuacion_anomalia"]
                )

                if datos.empty:

                    st.info("No hay puntuaciones disponibles.")

                else:

                    figura = go.Figure()

                    fragmentos = [
                        escape(str(t)[:130])
                        + ("…" if len(str(t)) > 130 else "")
                        for t in datos[texto]
                    ]

                    figura.add_scatter(
                        x=datos["puntuacion_anomalia"],
                        y=datos[fuente].astype(str).map(escape),
                        mode="markers",
                        marker=dict(
                            color=colores[0],
                            size=9,
                            opacity=0.70,
                            line=dict(
                                color="#FFFFFF",
                                width=0.5
                            )
                        ),
                        customdata=fragmentos,
                        hovertemplate=(
                            "%{y}<br>Puntuación: %{x:.4f}"
                            "<br>%{customdata}"
                            "<extra></extra>"
                        ),
                        showlegend=False
                    )

                    figura.update_xaxes(
                        title="Puntuación registrada"
                    )

                    figura.update_yaxes(
                        autorange="reversed"
                    )

                    mostrar_grafica(
                        figura,
                        "atipicos_puntuaciones",
                        205
                    )

                    st.caption(
                        "Cada punto representa un texto. "
                        "Pasa el cursor para leer un fragmento."
                    )


    if "texto_lexico" in outliers.columns:

        ngramas = analizar_ngramas(
            outliers["texto_lexico"].fillna("").tolist(),
            idioma=meta.get("idioma", "es"),
            bilingue=True,
            max_resultados=30
        )

        recalculados = True

    else:

        ngramas = guardados.copy()
        recalculados = False

    st.markdown("### Vocabulario de los textos atípicos")

    columnas = st.columns(3)

    for espacio, tipo, titulo, color in zip(
        columnas,
        ["unigrama", "bigrama", "trigrama"],
        ["Unigramas", "Bigramas", "Trigramas"],
        colores
    ):

        with espacio:
            with st.container(border=True):

                st.markdown(f"**{titulo}**")

                frecuentes = ngramas[
                    ngramas["tipo"].eq(tipo)
                ].sort_values(
                    "frecuencia",
                    ascending=False
                ).head(5)

                if frecuentes.empty:

                    st.caption("Sin expresiones disponibles.")
                    continue

                figura = go.Figure()

                figura.add_bar(
                    x=frecuentes["frecuencia"],
                    y=frecuentes["expresion"].astype(str).map(escape),
                    orientation="h",
                    marker_color=color,
                    text=frecuentes["frecuencia"],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "%{y}<br>%{x} apariciones"
                        "<extra></extra>"
                    )
                )

                figura.update_xaxes(
                    rangemode="tozero",
                    tickformat="d",
                    dtick=max(
                        1,
                        int(frecuentes["frecuencia"].max() / 4)
                    ),
                    title="Apariciones"
                )

                figura.update_yaxes(
                    autorange="reversed",
                    showgrid=False
                )

                mostrar_grafica(
                    figura,
                    f"atipicos_{tipo}",
                    180
                )

    st.caption(
        "Frecuencias sobre palabras normalizadas. "
        "No representan necesariamente frases literales "
        "ni explican por sí solas las anomalías."
    )


    @st.dialog("Explorar textos atípicos", width="large")
    def explorar():

        origen = st.selectbox(
            "Fuente",
            [None] + sorted(anomalos.index.tolist()),
            format_func=lambda f: "Todas las fuentes" if f is None else f
        )

        seleccion = outliers.copy()

        if origen is not None:

            seleccion = seleccion[
                seleccion[fuente].astype(str).eq(origen)
            ]

        seleccion = seleccion.reset_index(drop=True)

        def etiqueta(i):

            fila = seleccion.loc[i]
            fragmento = " ".join(
                str(fila[texto]).split()
            )

            return (
                f"{fila[fuente]} · {fragmento[:85]}"
                + ("…" if len(fragmento) > 85 else "")
            )

        indice = st.selectbox(
            "Publicación",
            seleccion.index.tolist(),
            format_func=etiqueta
        )

        fila = seleccion.loc[indice]

        a, b = st.columns(2)

        a.metric("Fuente", str(fila[fuente]))

        valor = pd.to_numeric(
            fila.get("puntuacion_anomalia"),
            errors="coerce"
        )

        b.metric(
            "Puntuación",
            f"{valor:.4f}" if pd.notna(valor)
            else "No disponible"
        )

        st.markdown("**Texto original recibido**")

        st.html(f"""
        <div style="
            background:#F5F7FA;
            border-left:4px solid {colores[0]};
            padding:14px;
            border-radius:8px;
            white-space:pre-wrap;
            overflow-wrap:anywhere;">
            {escape(str(fila[texto]))}
        </div>
        """)

        st.caption(
            "Una anomalía estadística no implica "
            "que el texto sea falso o irrelevante."
        )

        with st.expander("Consultar frecuencias"):

            st.dataframe(
                ngramas.rename(columns={
                    "tipo": "Tipo",
                    "expresion": "Expresión",
                    "frecuencia": "Apariciones"
                }),
                width="stretch",
                hide_index=True
            )

            if recalculados:

                st.caption(
                    "Frecuencias recalculadas para el tablero "
                    "con filtrado bilingüe adicional."
                )

                st.markdown("**Resultados originales guardados**")

                st.dataframe(
                    guardados,
                    width="stretch",
                    hide_index=True
                )

        with st.expander("Distribución completa por fuente"):

            st.dataframe(
                distribucion.reset_index().rename(
                    columns={"index": "Fuente", fuente: "Fuente"}
                ).round(2),
                width="stretch",
                hide_index=True
            )

    izquierda, derecha = st.columns([3, 1.4])

    with izquierda:

        st.caption(
            "Los atípicos se excluyen del modelado de temas, "
            "pero permanecen en el análisis económico."
        )

    with derecha:

        if st.button(
            "Explorar textos atípicos",
            width="stretch",
            key="explorar_atipicos_dashboard"
        ):
            explorar()
