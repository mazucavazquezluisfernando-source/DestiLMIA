import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def preparar_datos(tablas):

    resumen = tablas["sentimientos"].copy()

    columnas_entrada = tablas["entrada"].columns
    candidatas = [
        col for col in resumen.columns
        if col in columnas_entrada
    ]

    if len(candidatas) != 1:
        raise ValueError(
            "No se pudo identificar la columna de fuentes."
        )

    fuente = candidatas[0]

    metadatos = tablas["metadatos"]

    etiqueta_dmo = str(metadatos["etiqueta_dmo"])

    fuentes = resumen[fuente].astype(str)

    resumen["tipo_imagen"] = fuentes.map(
        lambda valor: (
            "DMO" if valor == etiqueta_dmo else "Usuarios"
        )
    )

    columnas = [
        "documentos",
        "positivos",
        "neutrales",
        "negativos",
        "binarios_positivos",
        "binarios_negativos",
    ]

    for columna in columnas:
        resumen[columna] = pd.to_numeric(
            resumen[columna], errors="raise"
        )

    grupos = (
        resumen.groupby("tipo_imagen", as_index=False)[columnas]
        .sum()
    )

    return resumen, grupos, fuente


def render_sentimiento_dinamico(tablas, carpeta):

    from collections import Counter
    from html import escape
    from plotly.colors import sample_colorscale
    from spacy.lang.es.stop_words import STOP_WORDS as STOP_ES
    from spacy.lang.en.stop_words import STOP_WORDS as STOP_EN
    import re

    from src.tema_global import (
        obtener_paleta,
        mostrar_kpis,
        mostrar_grafica
    )

    from src.vista_temas_sentimiento import etiquetas_tematicas

    resumen, grupos, fuente = preparar_datos(tablas)

    detalle = tablas["sentimientos_detalle"].copy()

    paleta = obtener_paleta(carpeta)

    clases = {
        "positivo": "positivos",
        "neutral": "neutrales",
        "negativo": "negativos"
    }

    colores = dict(zip(
        clases,
        sample_colorscale(paleta, [0.72, 0.40, 0.10])
    ))

    total = int(resumen["documentos"].sum())

    cantidades = {
        nombre: int(resumen[campo].sum())
        for nombre, campo in clases.items()
    }

    def porcentaje(n):
        return n / total * 100 if total else 0

    st.markdown("## Opiniones, sentimiento y temas frecuentes")

    st.caption(
        "¿Qué se dice sobre el destino? "
        "Distribución del sentimiento y contenido de los textos."
    )


    mostrar_kpis([
        (
            "Textos analizados",
            f"{total:,}",
            "Documentos evaluados"
        ),
        *[
            (
                f"Textos {nombre}s",
                f"{porcentaje(n):.1f}%",
                f"{n:,} textos"
            )
            for nombre, n in cantidades.items()
        ]
    ], paleta)

    if not total:
        st.info("No hay textos con sentimiento evaluado.")
        return

    izquierda, centro, derecha = st.columns([1, 1.2, 1.2])


    with izquierda:
        with st.container(border=True):

            st.markdown("**Distribución del sentimiento**")

            figura = go.Figure(go.Pie(
                labels=[c.capitalize() for c in clases],
                values=list(cantidades.values()),
                marker=dict(
                    colors=list(colores.values()),
                    line=dict(color="#FFFFFF", width=2)
                ),
                hole=0.65,
                sort=False,
                textinfo="percent",
                textposition="inside",
                hovertemplate=(
                    "%{label}<br>%{value} textos"
                    "<br>%{percent}<extra></extra>"
                ),
                showlegend=False
            ))

            figura.add_annotation(
                text=f"<b>{total:,}</b><br>textos",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=19)
            )

            mostrar_grafica(
                figura,
                "opiniones_dona",
                205
            )

            for nombre, n in cantidades.items():

                st.html(f"""
                <div style="display:flex;
                justify-content:space-between;
                align-items:center;font-size:12px;">
                    <span>
                        <span style="color:{colores[nombre]};">
                            ●
                        </span>
                        {nombre.capitalize()}
                    </span>
                    <strong>{porcentaje(n):.1f}% ({n:,})</strong>
                </div>
                """)


    with centro:
        with st.container(border=True):

            st.markdown("**Términos más frecuentes**")

            stopwords = STOP_ES | STOP_EN
            frecuencias = Counter()

            for contenido in detalle["texto_lexico"].dropna():

                palabras = re.findall(
                    r"[^\W\d_]+",
                    str(contenido).lower()
                )

                frecuencias.update(
                    p for p in palabras
                    if len(p) >= 3 and p not in stopwords
                )

            frecuentes = frecuencias.most_common(6)

            if frecuentes:

                palabras, valores = zip(*frecuentes)

                figura = go.Figure(go.Bar(
                    x=valores,
                    y=palabras,
                    orientation="h",
                    marker_color=sample_colorscale(
                        paleta,
                        [
                            0.15 + i * 0.65 / max(1, len(palabras)-1)
                            for i in range(len(palabras))
                        ]
                    ),
                    text=valores,
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "%{y}<br>%{x} apariciones"
                        "<extra></extra>"
                    )
                ))

                figura.update_yaxes(
                    autorange="reversed",
                    showgrid=False
                )

                figura.update_xaxes(
                    rangemode="tozero",
                    tickformat="d",
                    title="Apariciones"
                )

                mostrar_grafica(
                    figura,
                    "opiniones_vocabulario",
                    265
                )

            else:
                st.info("Sin vocabulario disponible.")

            st.caption("Palabras normalizadas del corpus evaluado.")


    with derecha:
        with st.container(border=True):

            st.markdown("**Comentarios destacados**")

            for nombre, color in colores.items():

                seleccion = detalle[
                    detalle["sentimiento"].eq(nombre)
                ].copy()

                if seleccion.empty:
                    st.caption(f"Sin textos de clase {nombre}.")
                    continue

                seleccion["confianza_sentimiento"] = pd.to_numeric(
                    seleccion["confianza_sentimiento"],
                    errors="coerce"
                )

                fila = seleccion.sort_values(
                    "confianza_sentimiento",
                    ascending=False
                ).iloc[0]

                contenido = " ".join(
                    str(fila["texto_entrada"]).split()
                )

                fragmento = contenido[:140]

                if len(contenido) > 140:
                    fragmento += "…"

                st.html(f"""
                <div style="border:1px solid #E3E8EF;
                border-left:4px solid {color};
                border-radius:8px;padding:9px;
                margin-bottom:5px;">
                    <div style="display:flex;
                    justify-content:space-between;
                    font-size:11px;gap:8px;">
                        <strong>{nombre.capitalize()}</strong>
                        <span style="color:#526174;">
                            {escape(str(fila["fuente_entrada"]))}
                        </span>
                    </div>
                    <div style="font-size:12px;
                    line-height:1.4;margin-top:4px;">
                        {escape(fragmento)}
                    </div>
                </div>
                """)

            st.caption(
                "Ejemplos con mayor confianza del clasificador."
            )

    izquierda, derecha = st.columns([1.65, 1])


    with izquierda:
        with st.container(border=True):

            st.markdown("**Temas más mencionados**")

            temas = tablas["topicos"].copy()

            temas["topico"] = pd.to_numeric(
                temas["topico"], errors="coerce"
            )

            temas = temas[temas["topico"] >= 0]

            nombres = etiquetas_tematicas(temas, "topico")

            conteos = temas["topico"].value_counts().head(5)

            if conteos.empty:

                st.caption("No hay comunidades temáticas disponibles.")

            else:

                espacios = st.columns(len(conteos))

                colores_temas = sample_colorscale(
                    paleta,
                    [
                        0.15 + i * 0.65 / max(1, len(conteos)-1)
                        for i in range(len(conteos))
                    ]
                )

                for espacio, (tema, n), color in zip(
                    espacios, conteos.items(), colores_temas
                ):

                    nombre = nombres.get(
                        int(tema), f"Tema {int(tema)}"
                    )

                    proporcion = n / len(temas) * 100

                    with espacio:

                        st.html(f"""
                        <div style="border:1px solid #E3E8EF;
                        border-radius:8px;padding:8px;">
                            <div style="font-size:11px;
                            min-height:42px;overflow-wrap:anywhere;">
                                {escape(nombre)}
                            </div>
                            <strong style="font-size:21px;">
                                {proporcion:.1f}%
                            </strong>
                            <div style="height:6px;
                            background:#EDF0F4;border-radius:5px;">
                                <div style="height:6px;
                                width:{proporcion:.2f}%;
                                background:{color};
                                border-radius:5px;"></div>
                            </div>
                            <div style="font-size:11px;
                            color:#526174;margin-top:4px;">
                                {n:,} textos
                            </div>
                        </div>
                        """)

                st.caption(
                    "Porcentaje de documentos asignados a temas."
                )


    with derecha:
        with st.container(border=True):

            st.markdown("**Ideas clave**")

            mayor = max(cantidades.values())

            dominantes = [
                c for c, n in cantidades.items()
                if n == mayor
            ]

            st.write(
                f"**Sentimiento más frecuente:** "
                f"{' y '.join(dominantes)} "
                f"({porcentaje(mayor):.1f}%)."
            )

            positivos = int(
                resumen["binarios_positivos"].sum()
            )

            negativos = int(
                resumen["binarios_negativos"].sum()
            )

            st.write(
                f"**Clasificación binaria:** "
                f"{porcentaje(positivos):.1f}% positivos y "
                f"{porcentaje(negativos):.1f}% negativos."
            )

            dmo = grupos[
                grupos["tipo_imagen"].eq("DMO")
            ]

            if not dmo.empty:

                n_dmo = dmo["documentos"].sum()

                if n_dmo:

                    neutral = dmo["neutrales"].sum() / n_dmo * 100

                    st.write(
                        f"**Comunicación oficial:** "
                        f"{neutral:.1f}% de textos neutrales."
                    )

            st.caption(
                "La clasificación binaria reasigna los neutrales."
            )


    @st.dialog("Explorar opiniones", width="large")
    def explorar_opiniones():

        vista = st.segmented_control(
            "Exploración",
            ["Comparaciones", "Comentarios"],
            default="Comparaciones"
        ) or "Comparaciones"

        if vista == "Comparaciones":

            for datos, eje, titulo in [
                (grupos, "tipo_imagen", "DMO frente a usuarios"),
                (resumen, fuente, "Comparación por fuente")
            ]:

                st.markdown(f"**{titulo}**")

                espacios = st.columns(2)

                for espacio, modo, campos in [
                    (
                        espacios[0],
                        "Original",
                        clases
                    ),
                    (
                        espacios[1],
                        "Binaria",
                        {
                            "positivo": "binarios_positivos",
                            "negativo": "binarios_negativos"
                        }
                    )
                ]:

                    with espacio:

                        st.caption(modo)

                        figura = go.Figure()

                        denominador = datos["documentos"].replace(
                            0, float("nan")
                        )

                        for nombre, campo in campos.items():

                            valores = datos[campo].div(
                                denominador
                            ).mul(100)

                            figura.add_bar(
                                name=nombre.capitalize(),
                                x=valores,
                                y=datos[eje].astype(str).map(escape),
                                orientation="h",
                                marker=dict(
                                    color=colores[nombre],
                                    pattern=dict(shape={
                                        "positivo": "/",
                                        "neutral": "",
                                        "negativo": "x"
                                    }[nombre])
                                ),
                                customdata=datos[campo],
                                text=[
                                    f"{v:.0f}%" if v >= 12 else ""
                                    for v in valores
                                ],
                                textposition="inside",
                                hovertemplate=(
                                    "%{y}<br>%{x:.1f}%"
                                    "<br>%{customdata} textos"
                                    "<extra></extra>"
                                )
                            )

                        figura.update_layout(barmode="stack")

                        figura.update_xaxes(
                            range=[0, 100],
                            ticksuffix="%"
                        )

                        figura.update_yaxes(
                            autorange="reversed"
                        )

                        mostrar_grafica(
                            figura,
                            f"opiniones_{eje}_{modo}",
                            max(165, 100 + 30 * len(datos))
                        )

            st.caption(
                "Los textos originalmente neutrales se reasignan "
                "según su mayor probabilidad positiva o negativa."
            )

            with st.expander("Consultar datos completos"):

                st.dataframe(
                    resumen,
                    hide_index=True,
                    width="stretch"
                )

                st.dataframe(
                    grupos,
                    hide_index=True,
                    width="stretch"
                )

        else:

            sentimiento = st.selectbox(
                "Sentimiento original",
                list(clases)
            )

            seleccion = detalle[
                detalle["sentimiento"].eq(sentimiento)
            ]

            origenes = sorted(
                seleccion["fuente_entrada"].astype(str).unique()
            )

            origen = st.selectbox(
                "Fuente",
                ["Todas"] + origenes
            )

            if origen != "Todas":

                seleccion = seleccion[
                    seleccion["fuente_entrada"].astype(str).eq(origen)
                ]

            seleccion = seleccion.reset_index(drop=True)

            if seleccion.empty:
                st.info("No hay comentarios en esta selección.")
                return

            indice = st.selectbox(
                "Publicación",
                seleccion.index.tolist(),
                format_func=lambda i: (
                    f"{i + 1}. "
                    + str(seleccion.loc[i, "texto_entrada"])[:80]
                )
            )

            fila = seleccion.loc[indice]

            st.caption(f"Fuente: {fila['fuente_entrada']}")

            st.text(str(fila["texto_entrada"]))

            st.caption(
                f"Sentimiento original: {fila['sentimiento']} · "
                f"Clasificación binaria: {fila['polaridad_binaria']}"
            )

    izquierda, derecha = st.columns([3, 1])

    with izquierda:

        st.caption(
            "El sentimiento se estima con hasta 512 tokens del texto, "
            "no necesariamente al destino ni a un tema específico."
        )

    with derecha:

        if st.button(
            "Explorar opiniones",
            width="stretch",
            key="explorar_opiniones_dashboard"
        ):
            explorar_opiniones()
