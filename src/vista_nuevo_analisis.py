import re
from io import BytesIO

import pandas as pd
import streamlit as st

from src.lanzador_analisis import iniciar_analisis, consultar_estado, TRABAJOS
from src.entrada_cli import leer_csv, es_columna_textual, preparar_entrada


def render_nuevo_analisis():

    st.title("Analiza un nuevo destino")

    st.write(
        "Compara la información publicada por un organismo "
        "turístico con los comentarios de otras fuentes. "
        "Comienza cargando un archivo CSV."
    )

    st.subheader("1. Carga tus comentarios")

    archivo = st.file_uploader(
        "Selecciona un archivo CSV",
        type=["csv"],
        key="archivo_nuevo_analisis"
    )

    if archivo is None:
        st.caption(
            "Tu archivo debe contener una columna de textos "
            "y otra que identifique la fuente de cada texto."
        )
        return

    if archivo.size > 30 * 1024 * 1024:
        st.error(
            "El archivo supera el límite de 30 MB "
            "establecido para esta pantalla."
        )
        return

    try:
        datos = leer_csv(BytesIO(archivo.getvalue()))
    except (ValueError, UnicodeError, pd.errors.ParserError) as error:
        st.error(f"No fue posible leer el CSV: {error}")
        return

    if datos.empty or len(datos.columns) < 2:
        st.error(
            "El archivo debe contener registros y "
            "al menos dos columnas."
        )
        return

    st.caption(
        f"Archivo leído: {len(datos):,} registros "
        f"y {len(datos.columns)} columnas."
    )

    st.subheader("2. Identifica tus columnas")

    columnas = datos.columns.tolist()

    columnas_texto = [
        columna
        for columna in columnas
        if es_columna_textual(datos[columna])
    ]

    if not columnas_texto:
        st.error(
            "Este archivo no contiene columnas de texto. "
            "DestiLMIA analiza comentarios escritos, "
            "no mediciones numéricas."
        )
        st.info(
            "Carga un CSV que incluya una columna "
            "de comentarios y otra que identifique "
            "su fuente."
        )
        return

    izquierda, derecha = st.columns(2)

    with izquierda:
        columna_texto = st.selectbox(
            "¿Dónde están los comentarios?",
            columnas_texto,
            key="nuevo_columna_texto"
        )

    with derecha:
        columna_fuente = st.selectbox(
            "¿Qué columna identifica la fuente?",
            columnas,
            index=1,
            key="nuevo_columna_fuente"
        )

    if columna_texto == columna_fuente:
        st.warning(
            "Selecciona columnas diferentes para "
            "los comentarios y las fuentes."
        )
        return

    textos = (
        datos[columna_texto]
        .astype("string")
        .str.strip()
        .fillna("")
    )

    fuentes = (
        datos[columna_fuente]
        .astype("string")
        .str.strip()
        .fillna("")
    )

    etiquetas = sorted(
        fuente for fuente in fuentes.unique()
        if fuente
    )

    if len(etiquetas) < 2:
        st.error(
            "Se necesitan al menos dos fuentes diferentes."
        )
        return

    st.subheader("3. Configura el análisis")

    dmo = st.selectbox(
        "¿Cuál es la fuente oficial del destino?",
        etiquetas,
        key="nuevo_dmo"
    )

    titulo = st.text_input(
        "Nombre del análisis",
        value=f"Análisis de {archivo.name.rsplit('.', 1)[0]}",
        key="nuevo_titulo"
    )

    a, b, c = st.columns(3)

    with a:
        st.selectbox(
            "Idioma",
            ["Español", "Inglés"],
            key="nuevo_idioma"
        )

    with b:
        st.selectbox(
            "Colores de las gráficas",
            ["cividis", "viridis", "plasma", "inferno"],
            key="nuevo_paleta"
        )

    with c:
        st.selectbox(
            "Procedencia de los datos",
            [
                "No especificada",
                "Datos reales",
                "Datos sintéticos",
                "Datos mixtos"
            ],
            key="nuevo_tipo_datos"
        )

    st.subheader("4. Revisa la información")

    validos = textos.ne("") & fuentes.ne("")
    oficiales = validos & fuentes.eq(dmo)
    usuarios = validos & fuentes.ne(dmo)

    n_oficiales = int(oficiales.sum())
    n_usuarios = int(usuarios.sum())
    n_invalidos = int((~validos).sum())

    a, b, c = st.columns(3)

    a.metric("Textos oficiales", n_oficiales)
    b.metric("Textos de otras fuentes", n_usuarios)
    c.metric("Registros sin texto o fuente", n_invalidos)

    with st.expander("Ver una muestra del archivo"):
        st.dataframe(
            datos[[columna_texto, columna_fuente]].head(5),
            hide_index=True,
            width="stretch"
        )


    if n_oficiales == 0 or n_usuarios == 0:
        st.error(
            "Necesitamos textos válidos de la fuente oficial "
            "y de al menos otra fuente."
        )
        return

    if n_invalidos > 0:
        st.error(
            "Hay registros sin texto o fuente. "
            "Corrige el archivo antes de continuar."
        )
        return

    if not titulo.strip():
        st.warning("Escribe un nombre para el análisis.")
        return

    try:
        preparar_entrada(datos, columna_texto, columna_fuente, dmo)
    except ValueError as error:
        st.error(str(error))
        return
    st.success("Los datos cumplen las comprobaciones preliminares.")

    st.subheader("5. Inicia el análisis")

    st.write(
        "DestiLMIA procesará los textos con el motor local "
        "y guardará los resultados para consultarlos después."
    )

    identificador = st.session_state.get("nuevo_trabajo_id")

    if identificador:
        estado = consultar_estado(identificador)
    else:
        estado = None

    en_proceso = (
        estado is not None
        and estado.get("estado") in ["iniciado", "procesando"]
    )

    if st.button(
        "Iniciar análisis",
        type="primary",
        disabled=en_proceso,
        key="boton_iniciar_destilmia"
    ):
        idioma = (
            "es"
            if st.session_state["nuevo_idioma"] == "Español"
            else "en"
        )

        try:
            identificador = iniciar_analisis(
                contenido=archivo.getvalue(),
                texto=columna_texto,
                fuente=columna_fuente,
                dmo=dmo,
                idioma=idioma,
                titulo=titulo.strip(),
                paleta=st.session_state["nuevo_paleta"],
                procedencia=st.session_state["nuevo_tipo_datos"]
            )

            st.session_state["nuevo_trabajo_id"] = identificador
            st.rerun()

        except (OSError, ValueError) as error:
            st.error(f"No se pudo iniciar el análisis: {error}")

    if identificador:

        @st.fragment(run_every=3 if en_proceso else None)
        def mostrar_estado():

            estado = consultar_estado(identificador)
            situacion = estado.get("estado")
            activo = situacion in ("iniciado", "procesando")

            if activo != en_proceso:
                st.rerun()

            st.markdown("#### Estado del análisis")

            if activo:
                st.info(
                    "Procesando análisis. Esto puede tardar varios "
                    "minutos o más con archivos grandes."
                )

                ruta_log = TRABAJOS / identificador / "procesamiento.log"

                log = ruta_log.read_text(
                    encoding="utf-8", errors="replace"
                ) if ruta_log.exists() else ""

                etapa = "Preparando datos"

                for marca, nombre in [
                    ("PREPROCESAMIENTO COMPLETADO", "Generando embeddings"),
                    ("EMBEDDINGS COMPLETADOS", "Detectando atípicos"),
                    ("DETECCION DE OUTLIERS COMPLETADA", "Alineación y n-gramas"),
                    ("ANALISIS DE N-GRAMAS COMPLETADO", "Analizando sentimientos"),
                    ("ANALISIS DE SENTIMIENTOS COMPLETADO", "Identificando temas"),
                    ("TOPICOS POR SENTIMIENTO COMPLETADOS", "Visualizaciones y análisis económico"),
                    ("SCATTER DE PRECIO Y VALOR COMPLETADO", "Comparando DMO y usuarios"),
                    ("COMPARACION TEMATICA DMO-USUARIOS COMPLETADA", "Guardando resultados")
                ]:
                    if marca in log:
                        etapa = nombre

                st.write(f"**Etapa actual:** {etapa}")

                avances = re.findall(r"Sentimientos: (\\d+)/(\\d+)", log)

                if avances and etapa == "Analizando sentimientos":
                    hechos, total = map(int, avances[-1])
                    if total > 0 and 0 <= hechos <= total:
                        st.progress(
                            hechos / total,
                            text=f"{hechos:,} de {total:,} comentarios clasificados"
                        )

                st.caption("Actualización automática cada 3 segundos.")

            elif situacion == "finalizado":
                st.success("¡Análisis terminado correctamente!")
                st.write("Resultados guardados. Ya puedes explorarlos.")

                def abrir_resultado():
                    st.session_state["abrir_resultado"] = estado["carpeta_resultados"]
                    st.session_state["accion_destilmia"] = "Explorar resultados"

                if st.button("Ver resultados", on_click=abrir_resultado, type="primary"):
                    st.rerun()

            elif situacion == "error":
                st.error("El análisis no pudo completarse.")
                st.caption(estado.get("mensaje", "Revisa el registro local."))

            else:
                st.warning("No se pudo determinar el estado del análisis.")

        mostrar_estado()
