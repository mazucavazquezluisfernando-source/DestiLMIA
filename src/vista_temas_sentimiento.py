import pandas as pd
import streamlit as st


from collections import Counter
from math import ceil, log, sqrt
import re

from spacy.lang.es.stop_words import STOP_WORDS as STOP_ES
from spacy.lang.en.stop_words import STOP_WORDS as STOP_EN


@st.cache_data(show_spinner=False)
def etiquetas_tematicas(datos, columna):


    texto = (
        "texto_limpio" if "texto_limpio" in datos
        else "texto_lexico"
    )

    stopwords = STOP_ES | STOP_EN

    grupos = {}
    tamanos = Counter()
    total = Counter()

    for tema, contenido in datos[[columna, texto]].itertuples(
        index=False, name=None
    ):

        if pd.isna(tema) or int(tema) < 0:
            continue

        tema = int(tema)
        tamanos[tema] += 1

        palabras = re.findall(
            r"[^\W\d_]+",
            str(contenido).lower()
        ) if pd.notna(contenido) else []

        expresiones = set()

        for n in (1, 2, 3):

            for i in range(len(palabras) - n + 1):

                frase = palabras[i:i+n]

                if (
                    frase[0] in stopwords
                    or frase[-1] in stopwords
                    or len(frase[0]) < 3
                    or len(frase[-1]) < 3
                ):
                    continue

                if len(set(frase)) != len(frase):
                    continue

                expresiones.add(" ".join(frase))

        grupos.setdefault(
            tema, Counter()
        ).update(expresiones)

        total.update(expresiones)

    n = sum(tamanos.values())
    etiquetas = {}

    for tema, conteo in grupos.items():

        m = tamanos[tema]
        soporte = max(2, ceil(m * 0.03))

        def puntuacion(frase):

            dentro = conteo[frase] / m

            if n == m:
                contraste = 1
            else:
                fuera = (
                    (total[frase] - conteo[frase])
                    / (n - m)
                )

                contraste = log(
                    (dentro + 0.01)
                    / (fuera + 0.01)
                )

            peso = 1.25 if " " in frase else 1

            return sqrt(dentro) * contraste * peso

        candidatos = sorted(
            [
                frase for frase in conteo
                if conteo[frase] >= soporte
                and puntuacion(frase) > 0
            ],
            key=lambda f: (-puntuacion(f), f)
        )

        elegidas = []

        for frase in candidatos:

            palabras_frase = set(frase.split()) - stopwords

            repetida = any(
                palabras_frase.intersection(
                    set(anterior.split()) - stopwords
                )
                for anterior in elegidas
            )

            if repetida:
                continue

            if elegidas and (
                puntuacion(frase)
                < puntuacion(elegidas[0]) * 0.6
            ):
                break

            elegidas.append(frase)

            if len(elegidas) == 2:
                break

        nombre = " · ".join(
            f.capitalize() for f in elegidas
        )

        if not nombre:
            nombre = "Sin etiqueta suficientemente representativa"
        elif n == m:
            nombre = "Expresiones frecuentes: " + nombre

        etiquetas[tema] = f"{nombre} (#{tema})"

    return etiquetas


def preparar_temas_sentimiento(tablas):

    documentos = tablas["topicos_polaridad"].copy()
    representantes = tablas["representativos"].copy()

    candidatas = [
        columna
        for columna in tablas["sentimientos"].columns
        if columna in tablas["entrada"].columns
        and columna in documentos.columns
    ]

    if "fuente_entrada" in candidatas:
        candidatas = ["fuente_entrada"]

    if len(candidatas) != 1:
        raise ValueError(
            "No se pudo identificar la columna de fuentes."
        )

    fuente = candidatas[0]

    documentos["topico_sentimiento"] = pd.to_numeric(
        documentos["topico_sentimiento"],
        errors="coerce"
    )

    representantes["topico"] = pd.to_numeric(
        representantes["topico"],
        errors="coerce"
    )

    return documentos, representantes, fuente


def grafica_ranking(conteos, color):

    import plotly.graph_objects as go
    from html import escape

    figura = go.Figure()

    figura.add_bar(
        x=conteos.values,
        y=[escape(str(t)) for t in conteos.index],
        orientation="h",
        marker_color=color,
        text=conteos.values,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x} textos<extra></extra>"
    )

    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(rangemode="tozero", dtick=max(1, int(conteos.max()/5)))

    return figura


@st.cache_data(show_spinner=False)
def vocabulario_tema(textos, idioma):

    from src.ngramas_outliers import analizar_ngramas

    return analizar_ngramas(
        textos,
        idioma=idioma,
        bilingue=True
    )


@st.cache_data(show_spinner=False)
def leer_mapas(archivo, version):

    import json

    contenido = archivo.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    figuras = []

    patron = r'Plotly\.newPlot\s*\(\s*"[^"]+"\s*,\s*'

    for coincidencia in re.finditer(patron, contenido):

        try:
            resto = contenido[coincidencia.end():].lstrip()

            datos, fin = decoder.raw_decode(resto)

            resto = resto[fin:].lstrip()

            if not resto.startswith(","):
                continue

            layout, _ = decoder.raw_decode(
                resto[1:].lstrip()
            )

            if isinstance(datos, list) and isinstance(layout, dict):
                figuras.append((datos, layout))

        except (ValueError, TypeError):
            continue

    return figuras


def render_dashboard_temas(tablas, carpeta, mostrar_mapa):

    import plotly.graph_objects as go
    from html import escape
    from pathlib import Path

    from src.tema_global import (
        obtener_paleta,
        colores_sentimiento,
        mostrar_kpis,
        mostrar_grafica
    )

    meta = tablas["metadatos"]
    paleta = obtener_paleta(carpeta)
    colores = colores_sentimiento(paleta)
    idioma = meta.get("idioma", "es")

    generales = tablas["topicos"].copy()

    generales["topico"] = pd.to_numeric(
        generales["topico"], errors="coerce"
    )

    generales = generales[
        generales["topico"] >= 0
    ].copy()

    documentos, representantes, fuente = (
        preparar_temas_sentimiento(tablas)
    )

    positivos = documentos[
        documentos["polaridad_binaria"] == "positivo"
    ]

    negativos = documentos[
        documentos["polaridad_binaria"] == "negativo"
    ]

    def contar_temas(datos):

        return datos.loc[
            datos["topico_sentimiento"] >= 0,
            "topico_sentimiento"
        ].nunique()

    st.markdown("## Temas y conversaciones")


    mostrar_kpis([
        (
            "Temas generales",
            generales["topico"].nunique(),
            "Comunidades identificadas"
        ),
        (
            "Textos agrupados",
            f"{len(generales):,}",
            "Modelado general"
        ),
        (
            "Temas positivos",
            contar_temas(positivos),
            f"{len(positivos):,} textos binarios"
        ),
        (
            "Temas negativos",
            contar_temas(negativos),
            f"{len(negativos):,} textos binarios"
        )
    ], paleta)

    izquierda, derecha = st.columns([1.65, 1])


    with izquierda:
        with st.container(border=True):

            st.markdown("**Mapa semántico de comentarios**")

            mapas = []

            for nombre in [
                "dispersion_comentarios.html",
                "topicos_por_sentimiento_scatter.html"
            ]:

                archivo = Path(carpeta) / nombre

                if not archivo.is_file():
                    continue

                figuras = leer_mapas(
                    archivo,
                    archivo.stat().st_mtime_ns
                )

                for numero, (datos, layout) in enumerate(figuras):

                    titulo = layout.get("title", {})

                    if isinstance(titulo, dict):
                        titulo = titulo.get("text", "")

                    titulo = titulo or f"Mapa {numero + 1}"

                    mapas.append({
                        "titulo": titulo,
                        "datos": datos,
                        "layout": layout,
                        "archivo": nombre
                    })

            if mapas:

                inicial = next(
                    (
                        i for i, mapa in enumerate(mapas)
                        if "tópico" in mapa["titulo"].lower()
                        and mapa["archivo"] == "dispersion_comentarios.html"
                    ),
                    0
                )

                elegido = st.selectbox(
                    "Visualización",
                    range(len(mapas)),
                    index=inicial,
                    format_func=lambda i: mapas[i]["titulo"],
                    label_visibility="collapsed",
                    key="mapa_temas_compacto"
                )

                mapa = mapas[elegido]

                figura = go.Figure(
                    data=mapa["datos"],
                    layout=mapa["layout"]
                )

                figura.update_layout(
                    title=None,
                    autosize=True,
                    width=None,
                    height=320,
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF",
                    font=dict(
                        family="Inter, Arial, sans-serif",
                        size=11,
                        color="#172334"
                    ),
                    margin=dict(l=5, r=5, t=12, b=25),
                    legend=dict(
                        orientation="v",
                        x=1.02,
                        y=1,
                        font=dict(size=10)
                    )
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
                    key="scatter_temas_principal",
                    config={"displaylogo": False}
                )

                st.caption(
                    "Pasa el cursor sobre un punto para consultar el texto."
                )

            else:

                st.info(
                    "Consulta las visualizaciones originales."
                )

                mostrar_mapa(
                    "dispersion_comentarios.html",
                    "mapa_alternativo",
                    450,
                    carpeta
                )


    with derecha:

        with st.container(border=True):

            st.markdown("**Sentimiento por tema**")

            nombres = etiquetas_tematicas(
                generales, "topico"
            )

            conteos = generales["topico"].value_counts().head(5)

            if not conteos.empty:

                matriz = pd.crosstab(
                    generales["topico"],
                    generales["sentimiento"]
                ).reindex(
                    index=conteos.index,
                    columns=["positivo", "neutral", "negativo"],
                    fill_value=0
                )

                porcentajes = matriz.div(
                    conteos, axis=0
                ).mul(100)

                etiquetas = [
                    escape(nombres.get(int(t), f"Tema {int(t)}"))
                    + f"<br>{conteos[t]} textos"
                    for t in conteos.index
                ]

                figura = go.Figure(go.Heatmap(
                    z=porcentajes.values,
                    x=["Pos.", "Neu.", "Neg."],
                    y=etiquetas,
                    colorscale=paleta,
                    zmin=0,
                    zmax=100,
                    texttemplate="%{z:.0f}%",
                    colorbar=dict(
                        title="%",
                        thickness=9
                    ),
                    customdata=matriz.values,
                    hovertemplate=(
                        "%{y}<br>%{x}: %{z:.1f}%"
                        "<br>%{customdata} textos"
                        "<extra></extra>"
                    )
                ))

                figura.update_yaxes(
                    autorange="reversed"
                )

                mostrar_grafica(
                    figura, "heatmap_temas_compacto", 220
                )

            else:
                st.caption("No hay comunidades generales.")

        with st.container(border=True):

            st.markdown("**Principales conversaciones**")

            for grupo, polaridad, color in [
                (positivos, "positivo", colores["Positivo"]),
                (negativos, "negativo", colores["Negativo"])
            ]:

                conteos = grupo.loc[
                    grupo["topico_sentimiento"] >= 0,
                    "topico_sentimiento"
                ].value_counts()

                st.caption(f"Mayor grupo de polaridad {polaridad}")

                if not conteos.empty:

                    nombres_grupo = etiquetas_tematicas(
                        grupo, "topico_sentimiento"
                    )

                    tema = int(conteos.index[0])
                    cantidad = int(conteos.iloc[0])

                    nombre = nombres_grupo.get(
                        tema, f"Tema {tema}"
                    )

                    st.html(f"""
                    <div style="display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:12px;">
                        <strong style="color:{color};">
                            {escape(nombre)}
                        </strong>
                        <strong style="font-size:20px;">
                            {cantidad}
                        </strong>
                    </div>
                    """)

                    if (conteos == cantidad).sum() > 1:
                        st.caption("Hay grupos empatados.")

                elif not grupo.empty:

                    st.caption(
                        "Método alternativo: frecuencia de palabras."
                    )

                else:
                    st.caption("Sin textos disponibles.")

            st.caption("Polaridad binaria con neutrales reasignados.")


    if st.toggle(
        "Explorar temas, palabras y comentarios",
        key="explorador_temas_compacto"
    ):

        tipo = st.radio(
            "Tipo de análisis",
            ["General", "Positivo", "Negativo"],
            horizontal=True
        )

        if tipo == "General":

            grupo = generales
            columna = "topico"

        else:

            grupo = positivos if tipo == "Positivo" else negativos
            columna = "topico_sentimiento"

        if grupo.empty:

            st.info("No hay textos en este conjunto.")
            return

        conteos = grupo[columna].value_counts()

        if conteos.empty:
            st.info("No hay grupos disponibles.")
            return

        nombres = etiquetas_tematicas(grupo, columna)

        tema = st.selectbox(
            "Tema",
            conteos.index.tolist(),
            format_func=lambda t: (
                f"{nombres.get(int(t), 'Frecuencias sin comunidad')}"
                f" · {conteos[t]} textos"
            ),
            key=f"detalle_tema_{tipo}"
        )

        seleccion = grupo[grupo[columna] == tema]

        izquierda, derecha = st.columns(2)

        with izquierda:
            with st.container(border=True):

                st.markdown("**Vocabulario del tema**")

                frecuencias = vocabulario_tema(
                    seleccion["texto_lexico"].fillna("").tolist(),
                    idioma
                )

                clase = st.radio(
                    "Expresiones",
                    ["unigrama", "bigrama", "trigrama"],
                    horizontal=True
                )

                ranking = frecuencias[
                    frecuencias["tipo"] == clase
                ].head(8).set_index("expresion")["frecuencia"]

                if not ranking.empty:

                    figura = grafica_ranking(
                        ranking, colores["Neutral"]
                    )

                    figura.update_traces(
                        hovertemplate=(
                            "%{y}<br>%{x} apariciones"
                            "<extra></extra>"
                        )
                    )

                    mostrar_grafica(
                        figura, "detalle_vocabulario", 245
                    )

                with st.expander("Todas las frecuencias"):

                    st.dataframe(
                        frecuencias,
                        hide_index=True,
                        width="stretch"
                    )

        with derecha:
            with st.container(border=True):

                st.markdown("**Fuentes del tema**")

                distribucion = seleccion[fuente].value_counts()

                st.dataframe(
                    distribucion.rename("Textos"),
                    width="stretch"
                )

                st.markdown("**Evidencia textual**")

                if tipo == "General":

                    st.caption("Ejemplos por fuente")

                    for _, fila in seleccion.groupby(fuente).head(1).iterrows():

                        with st.expander(str(fila[fuente])):
                            st.text(str(fila["texto_entrada"]))

                else:

                    ejemplos = representantes[
                        representantes["sentimiento"].eq(tipo.lower())
                        & representantes["topico"].eq(tema)
                    ]

                    if ejemplos.empty:
                        st.caption("Sin representante registrado.")

                    for _, fila in ejemplos.iterrows():

                        st.caption(f"Fuente: {fila['fuente']}")

                        st.text(str(fila["texto"]))

                    metodos = seleccion[
                        "metodo_sentimiento"
                    ].dropna().unique()

                    st.caption(
                        "Método: " + ", ".join(map(str, metodos))
                    )

    with st.expander("Visualizaciones originales"):

        for nombre in [
            "dispersion_comentarios.html",
            "topicos_por_sentimiento_scatter.html"
        ]:

            archivo = Path(carpeta) / nombre

            if archivo.is_file():

                st.download_button(
                    nombre,
                    data=archivo.read_bytes(),
                    file_name=nombre,
                    mime="text/html",
                    key=f"html_original_{nombre}"
                )

    st.caption(
        "Etiquetas automáticas. Los temas requieren interpretación textual."
    )
