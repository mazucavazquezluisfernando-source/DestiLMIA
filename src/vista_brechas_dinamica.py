import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def preparar_brechas(tablas):

    alineacion = tablas["alineacion"].copy()
    brechas = tablas["brechas"].copy()

    globales = alineacion[
        alineacion["tipo"] == "global"
    ].copy()

    por_fuente = alineacion[
        alineacion["tipo"] == "por_fuente"
    ].copy()

    if len(globales) != 1:
        raise ValueError(
            "Se esperaba una alineación global."
        )

    por_fuente["alineacion_coseno"] = pd.to_numeric(
        por_fuente["alineacion_coseno"],
        errors="raise"
    )

    brechas["similitud_coseno"] = pd.to_numeric(
        brechas["similitud_coseno"],
        errors="coerce"
    )

    return globales, por_fuente, brechas


def render_brechas_dinamica(tablas, carpeta, mostrar_mapa):

    from html import escape
    from plotly.colors import sample_colorscale

    from src.tema_global import (
        obtener_paleta,
        mostrar_kpis,
        mostrar_grafica
    )

    from src.vista_temas_sentimiento import etiquetas_tematicas

    globales, fuentes, brechas = preparar_brechas(tablas)

    paleta = obtener_paleta(carpeta)

    color_dmo, color_usuario = sample_colorscale(
        paleta, [0.15, 0.72]
    )

    color_fuente = sample_colorscale(
        paleta, [0.40]
    )[0]

    nombres = etiquetas_tematicas(
        tablas["topicos"], "topico"
    )

    similitud = pd.to_numeric(globales.iloc[0]["alineacion_coseno"], errors="coerce")

    archivo = carpeta / "presencia_tematica_dmo_usuarios.csv"

    if not archivo.is_file():

        st.warning("No existe el resumen de presencia temática.")
        return

    datos = pd.read_csv(archivo)

    columnas = [
        "documentos_dmo",
        "documentos_usuarios",
        "porcentaje_segmento_dmo",
        "porcentaje_segmento_usuarios"
    ]

    for columna in columnas:
        datos[columna] = pd.to_numeric(
            datos[columna], errors="coerce"
        )

    datos["Tema"] = datos["comunidad"].map(
        lambda t: nombres.get(int(t), f"Tema {int(t)}")
    )

    datos["Diferencia"] = (
        datos["porcentaje_segmento_usuarios"]
        - datos["porcentaje_segmento_dmo"]
    )

    datos["Brecha"] = datos["Diferencia"].abs()

    compartidos = (
        (datos["documentos_dmo"] > 0)
        & (datos["documentos_usuarios"] > 0)
    )

    solo_dmo = (
        (datos["documentos_dmo"] > 0)
        & (datos["documentos_usuarios"] == 0)
    )

    solo_usuarios = (
        (datos["documentos_dmo"] == 0)
        & (datos["documentos_usuarios"] > 0)
    )

    datos["Presencia"] = "Compartida"
    datos.loc[solo_dmo, "Presencia"] = "Solo DMO"
    datos.loc[solo_usuarios, "Presencia"] = "Solo usuarios"

    comparables = (
        datos["documentos_dmo"].sum() > 0
        and datos["documentos_usuarios"].sum() > 0
    )

    st.markdown("## Imagen proyectada frente a imagen percibida")


    mostrar_kpis([
        (
            "Alineación global",
            f"{similitud:.3f}" if pd.notna(similitud)
            else "No calculable",
            "Similitud coseno"
        ),
        (
            "Temas compartidos",
            int(compartidos.sum()),
            "Presentes en ambos grupos"
        ),
        (
            "Solo DMO",
            int(solo_dmo.sum()),
            "Comunidades exclusivas"
        ),
        (
            "Solo usuarios",
            int(solo_usuarios.sum()),
            "Comunidades exclusivas"
        )
    ], paleta)

    izquierda, derecha = st.columns([1.65, 1])


    with izquierda:
        with st.container(border=True):

            st.markdown(
                "**Brechas de presencia temática**"
            )

            vista = (
                datos.dropna(subset=["Brecha"])
                .sort_values("Brecha", ascending=False)
                .head(6)
            )

            if vista.empty or not comparables:

                st.info("No hay suficientes datos para comparar.")

            else:

                figura = go.Figure()

                etiquetas = [
                    escape(t) for t in vista["Tema"]
                ]

                lineas_x = []
                lineas_y = []

                for etiqueta, (_, fila) in zip(
                    etiquetas, vista.iterrows()
                ):

                    lineas_x.extend([
                        fila["porcentaje_segmento_dmo"],
                        fila["porcentaje_segmento_usuarios"],
                        None
                    ])

                    lineas_y.extend([
                        etiqueta,
                        etiqueta,
                        None
                    ])

                figura.add_scatter(
                    x=lineas_x,
                    y=lineas_y,
                    mode="lines",
                    line=dict(color="#C2CCD9", width=3),
                    showlegend=False,
                    hoverinfo="skip"
                )

                for grupo, campo, cantidad, color, forma, posicion in [
                    (
                        "DMO",
                        "porcentaje_segmento_dmo",
                        "documentos_dmo",
                        color_dmo,
                        "circle",
                        "top center"
                    ),
                    (
                        "Usuarios",
                        "porcentaje_segmento_usuarios",
                        "documentos_usuarios",
                        color_usuario,
                        "diamond",
                        "bottom center"
                    )
                ]:

                    figura.add_scatter(
                        name=grupo,
                        x=vista[campo],
                        y=etiquetas,
                        mode="markers+text",
                        marker=dict(
                            color=color,
                            symbol=forma,
                            size=11,
                            line=dict(color="#FFFFFF", width=1)
                        ),
                        text=[
                            f"{v:.1f}%"
                            for v in vista[campo]
                        ],
                        textposition=posicion,
                        textfont=dict(
                            color="#172334",
                            size=10
                        ),
                        customdata=vista[cantidad],
                        cliponaxis=False,
                        hovertemplate=(
                            "%{y}<br>" + grupo +
                            ": %{x:.1f}%"
                            "<br>%{customdata} textos"
                            "<extra></extra>"
                        )
                    )

                figura.update_xaxes(
                    range=[-5, 105],
                    tickvals=[0, 20, 40, 60, 80, 100],
                    ticksuffix="%",
                    title="Presencia dentro de cada universo"
                )

                figura.update_yaxes(
                    autorange="reversed",
                    categoryorder="array",
                    categoryarray=etiquetas,
                    showgrid=False
                )

                mostrar_grafica(
                    figura,
                    "brechas_dumbbell",
                    265
                )

                st.caption(
                    "Hasta seis temas con mayor diferencia. "
                    "La distancia representa puntos porcentuales."
                )


    with derecha:

        with st.container(border=True):

            st.markdown("**Similitud con la DMO**")

            ordenados = fuentes.dropna(
                subset=["alineacion_coseno"]
            ).sort_values(
                "alineacion_coseno", ascending=False
            )

            if ordenados.empty:

                st.info("No hay similitudes calculables.")

            else:

                vista = ordenados.head(5)

                if len(ordenados) > 5:
                    vista = pd.concat([
                        vista, ordenados.tail(1)
                    ]).drop_duplicates()

                figura = go.Figure()

                lineas_x = []
                lineas_y = []

                for _, fila in vista.iterrows():

                    nombre = escape(str(fila["fuente_percibida"]))

                    lineas_x.extend([
                        0,
                        fila["alineacion_coseno"],
                        None
                    ])

                    lineas_y.extend([
                        nombre, nombre, None
                    ])

                figura.add_scatter(
                    x=lineas_x,
                    y=lineas_y,
                    mode="lines",
                    line=dict(color="#BFCBD7", width=3),
                    hoverinfo="skip",
                    showlegend=False
                )

                figura.add_scatter(
                    x=vista["alineacion_coseno"],
                    y=[
                        escape(str(f))
                        for f in vista["fuente_percibida"]
                    ],
                    mode="markers+text",
                    marker=dict(
                        size=11,
                        color=color_fuente
                    ),
                    text=[
                        f"{v:.3f}"
                        for v in vista["alineacion_coseno"]
                    ],
                    textposition=[
                        "middle left" if v > 0.85
                        else "middle right"
                        for v in vista["alineacion_coseno"]
                    ],
                    showlegend=False,
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
                    dtick=0.5,
                    title="Similitud coseno"
                )

                figura.update_yaxes(
                    autorange="reversed",
                    showgrid=False
                )

                mostrar_grafica(
                    figura,
                    "similitud_lollipop",
                    265
                )

                if len(ordenados) > 6:
                    st.caption(
                        "Cinco fuentes más cercanas y la más distante."
                    )


    izquierda, derecha = st.columns([1.65, 1])

    with izquierda:
        with st.container(border=True):

            st.markdown("**Distribuciones comparativas**")

            from src.vista_temas_sentimiento import leer_mapas

            archivo = carpeta / "distribuciones_dmo_usuarios.html"

            figuras = (
                leer_mapas(archivo, archivo.stat().st_mtime_ns)
                if archivo.is_file() else []
            )

            if figuras:

                titulos = []

                for numero, (_, layout) in enumerate(figuras):

                    titulo = layout.get("title", {})

                    if isinstance(titulo, dict):
                        titulo = titulo.get("text", "")

                    titulos.append(titulo or f"Distribución {numero + 1}")

                elegido = 0

                if len(figuras) > 1:

                    elegido = st.selectbox(
                        "Distribución",
                        range(len(figuras)),
                        format_func=lambda i: titulos[i],
                        label_visibility="collapsed",
                        key="distribucion_dashboard"
                    )

                datos_grafica, layout = figuras[elegido]

                figura = go.Figure(
                    data=datos_grafica,
                    layout=layout
                )

                figura.update_layout(
                    title=None,
                    height=250,
                    width=None,
                    autosize=True,
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#FFFFFF",
                    font=dict(
                        family="Inter, Arial, sans-serif",
                        size=11,
                        color="#172334"
                    ),
                    margin=dict(l=10, r=15, t=30, b=35)
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
                    key="distribucion_integrada",
                    config={"displaylogo": False}
                )

            else:

                mostrar_mapa(
                    "distribuciones_dmo_usuarios.html",
                    "distribucion_alternativa",
                    350,
                    carpeta
                )

    with derecha:


        with st.container(border=True):

            st.markdown("**Diferencias más relevantes**")

            if comparables:

                for titulo, seleccion, color in [
                    (
                        "Mayor presencia en la DMO",
                        datos[datos["Diferencia"] < 0],
                        color_dmo
                    ),
                    (
                        "Mayor presencia entre usuarios",
                        datos[datos["Diferencia"] > 0],
                        color_usuario
                    )
                ]:

                    st.caption(titulo)

                    if seleccion.empty:

                        st.write("Sin diferencias en este sentido.")

                    else:

                        fila = seleccion.loc[
                            seleccion["Brecha"].idxmax()
                        ]

                        st.html(f"""
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            gap:12px;
                            padding-bottom:6px;
                        ">
                            <strong style="font-size:13px;">
                                {escape(fila["Tema"])}
                            </strong>
                            <strong style="
                                font-size:20px;
                                color:{color};
                                white-space:nowrap;
                            ">
                                {fila["Brecha"]:.1f} pp
                            </strong>
                        </div>
                        """)

            else:

                st.caption("Comparación no disponible.")

            st.caption("pp = puntos porcentuales.")

    st.caption(
        ""
        "La similitud semántica no mide satisfacción."
    )


    @st.dialog("Explorar diferencias temáticas", width="large")
    def explorar_evidencia():

        filtro = st.segmented_control(
            "Presencia temática",
            ["Todos", "Compartida", "Solo DMO", "Solo usuarios"],
            default="Todos",
            label_visibility="collapsed"
        ) or "Todos"

        seleccion = datos.copy()

        if filtro != "Todos":
            seleccion = seleccion[
                seleccion["Presencia"] == filtro
            ]

        seleccion = seleccion.sort_values(
            "Brecha", ascending=False
        )

        if seleccion.empty:
            st.info("No hay temas en esta categoría.")
            return

        tema = st.selectbox(
            "Selecciona una conversación",
            seleccion["comunidad"].tolist(),
            format_func=lambda t: nombres.get(
                int(t), f"Tema {int(t)}"
            )
        )

        fila = seleccion[
            seleccion["comunidad"] == tema
        ].iloc[0]

        izquierda, centro, derecha = st.columns(3)

        izquierda.metric(
            "Presencia DMO",
            f"{fila['porcentaje_segmento_dmo']:.1f}%"
            if pd.notna(fila["porcentaje_segmento_dmo"])
            else "No calculable"
        )

        centro.metric(
            "Presencia usuarios",
            f"{fila['porcentaje_segmento_usuarios']:.1f}%"
            if pd.notna(fila["porcentaje_segmento_usuarios"])
            else "No calculable"
        )

        derecha.metric(
            "Diferencia",
            f"{fila['Brecha']:.1f} pp"
            if comparables and pd.notna(fila["Brecha"])
            else "No calculable"
        )

        diferencia = fila["Diferencia"]

        if comparables and pd.notna(diferencia):

            if diferencia > 0:
                st.write(
                    "Esta comunidad tiene mayor presencia "
                    "entre los usuarios."
                )

            elif diferencia < 0:
                st.write(
                    "Esta comunidad tiene mayor presencia "
                    "en la comunicación oficial."
                )

            else:
                st.write(
                    "Ambos grupos tienen la misma "
                    "presencia proporcional."
                )

        st.caption(
            "La presencia temática no equivale "
            "a satisfacción ni importancia turística."
        )

        izquierda, derecha = st.columns(2)

        for espacio, grupo, campo, color in [
            (izquierda, "DMO", "dmo", color_dmo),
            (derecha, "Usuarios", "usuarios", color_usuario)
        ]:

            with espacio:
                with st.container(border=True):

                    cantidad = fila[f"documentos_{campo}"]

                    st.html(f"""
                    <div style="
                        border-left:4px solid {color};
                        padding-left:10px;">
                        <strong>{grupo}</strong>
                        <div style="font-size:24px;">
                            {int(cantidad)} textos
                        </div>
                    </div>
                    """)

                    if cantidad > 0:

                        st.caption("Vocabulario frecuente")

                        terminos = fila[f"terminos_{campo}"]

                        if pd.notna(terminos):
                            st.write(str(terminos))

                        st.caption(
                            "Tono predominante: "
                            + str(fila[f"tono_predominante_{campo}"])
                        )

                        with st.expander("Leer publicación de ejemplo"):

                            st.text(
                                str(fila[f"ejemplo_lexico_{campo}"])
                            )

                    else:

                        st.caption(
                            "Sin publicaciones en esta comunidad."
                        )

        coincidencia = brechas[
            brechas["comunidad_usuarios"] == tema
        ]

        if not coincidencia.empty:

            cercano = coincidencia.iloc[0]

            comunidad_dmo = cercano[
                "comunidad_dmo_mas_cercana"
            ]

            if pd.notna(comunidad_dmo):

                similitud = cercano["similitud_coseno"]

                with st.container(border=True):

                    st.caption("Coincidencia semántica más cercana")

                    nombre = nombres.get(
                        int(comunidad_dmo),
                        f"Tema {int(comunidad_dmo)}"
                    )

                    st.write(nombre)

                    if pd.notna(similitud):
                        st.markdown(f"**Similitud: {similitud:.3f}**")

                    if int(comunidad_dmo) != int(tema):

                        st.caption("Términos de la comunidad DMO")

                        st.write(
                            str(cercano["terminos_dmo_cercana"])
                        )

                    st.caption(
                        str(cercano["estado_interpretacion"])
                    )

        with st.expander("Consultar datos completos"):

            tabla = datos[[
                "Tema",
                "Presencia",
                "documentos_dmo",
                "documentos_usuarios",
                "porcentaje_segmento_dmo",
                "porcentaje_segmento_usuarios",
                "Diferencia"
            ]].rename(columns={
                "documentos_dmo": "Textos DMO",
                "documentos_usuarios": "Textos usuarios",
                "porcentaje_segmento_dmo": "DMO (%)",
                "porcentaje_segmento_usuarios": "Usuarios (%)",
                "Diferencia": "Usuarios − DMO (pp)"
            })

            st.dataframe(
                tabla.round(1),
                hide_index=True,
                width="stretch",
                height=250
            )

            st.dataframe(
                fuentes[[
                    "fuente_percibida",
                    "documentos_percibidos",
                    "alineacion_coseno"
                ]].rename(columns={
                    "fuente_percibida": "Fuente",
                    "documentos_percibidos": "Textos",
                    "alineacion_coseno": "Similitud"
                }).round(3),
                hide_index=True,
                width="stretch"
            )

        st.caption(
            "Las etiquetas son automáticas. "
            "Revisa el contenido antes de concluir "
            "que existe una brecha turística."
        )

    izquierda, derecha = st.columns([3, 1])

    with izquierda:

        st.caption(
            "Explora las publicaciones que sustentan "
            "las diferencias detectadas."
        )

    with derecha:

        if st.button(
            "Investigar una diferencia",
            width="stretch",
            key="abrir_evidencia_dmo"
        ):

            explorar_evidencia()
