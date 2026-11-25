#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 22:46:46 2026

@author: luismazuca
"""


from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

from src.carga_dashboard import cargar_tablas, analisis_completo
from src.vista_centro_control import (
    render_barra_control, render_panel_control, nombre_analisis
)
from src.vista_sentimiento_dinamico import render_sentimiento_dinamico
from src.vista_brechas_dinamica import render_brechas_dinamica
from src.vista_precio_dinamica import render_precio_dinamica
from src.vista_outliers_dinamica import render_outliers_dinamica

SECCIONES = [
    "Panorama", "Opiniones", "Temas",
    "DMO vs usuarios", "Precio y valor", "Atípicos"
]

ARCHIVOS_HTML = {
    "dispersion_comentarios.html",
    "topicos_por_sentimiento_scatter.html",
    "distribuciones_dmo_usuarios.html",
    "precio_valor_scatter.html"
}


def seleccionar_analisis():
    base = Path("resultados/cli")
    opciones = sorted(
        (
            carpeta for carpeta in base.glob("ejecucion_*")
            if carpeta.is_dir()
            and carpeta.name.rsplit("_", 1)[-1].isdigit()
            and analisis_completo(carpeta)
        ),
        key=lambda carpeta: int(carpeta.name.rsplit("_", 1)[-1]),
        reverse=True
    )

    if not opciones:
        return None

    nuevo = st.session_state.pop("abrir_resultado", None)
    if nuevo and Path(nuevo) in opciones:
        st.session_state["selector_analisis"] = Path(nuevo)

    if st.session_state.get("selector_analisis") not in opciones:
        st.session_state.pop("selector_analisis", None)

    return st.sidebar.selectbox(
        "Análisis disponible",
        opciones,
        format_func=nombre_analisis,
        key="selector_analisis"
    )


def mostrar_guia():
    with st.sidebar.popover("Guía de uso"):
        st.markdown("""
        **Cómo explorar DestiLMIA**

        1. Selecciona una sección del análisis.
        2. Utiliza los filtros para comparar fuentes y comunidades.
        3. Pasa el cursor sobre las gráficas para consultar detalles.
        4. Abre los exploradores para revisar comentarios.

        Los resultados son exploratorios. Considera el tamaño del
        corpus y las limitaciones de cada método.
        """)


def alternar_graficas(contenido, etiquetas):
    if "</body>" not in contenido or "plotly-graph-div" not in contenido:
        return contenido

    botones = "".join(
        f'<button type="button" data-vista="{i}">{escape(nombre)}</button>'
        for i, nombre in enumerate(etiquetas)
    )

    interfaz = r"""
<style>
body{max-width:none!important;margin:0!important;padding:4px!important}
body>h1{display:none!important}
body>p{font:12px/1.4 Arial,sans-serif;color:#60716F;
    margin:4px 10px 8px!important}
#destilmia-vistas{display:flex;gap:8px;flex-wrap:wrap;padding:8px 10px}
#destilmia-vistas button{border:1px solid #D4E4E0;background:white;
    border-radius:9px;padding:9px 13px;cursor:pointer;color:#34454B;
    font:13px Arial,sans-serif}
#destilmia-vistas button.activo{background:#E5F5F1;color:#087D75;
    border-color:#54ACA3;font-weight:bold}
</style>
<div id="destilmia-vistas">BOTONES</div>
<script>
(function () {
    function iniciar() {
        const barra = document.getElementById('destilmia-vistas');
        const graficas = Array.from(document.querySelectorAll('.plotly-graph-div'));
        if (!barra) return;

        const botones = Array.from(barra.querySelectorAll('button'));
        if (graficas.length !== botones.length) {
            barra.style.display = 'none';
            return;
        }

        const paneles = graficas.map(g => g.parentElement);
        paneles[0].parentElement.insertBefore(barra, paneles[0]);

        function mostrar(indice) {
            paneles.forEach((panel, i) => {
                panel.style.display = i === indice ? 'block' : 'none';
            });
            botones.forEach((boton, i) => {
                boton.classList.toggle('activo', i === indice);
            });
            requestAnimationFrame(() => {
                if (window.Plotly && window.Plotly.Plots) {
                    window.Plotly.Plots.resize(graficas[indice]);
                }
            });
        }

        botones.forEach((boton, i) => {
            boton.addEventListener('click', () => mostrar(i));
        });
        mostrar(0);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
</script>
"""
    interfaz = interfaz.replace("BOTONES", botones, 1)
    return contenido.replace("</body>", interfaz + "</body>", 1)


def compactar_html_mapa(contenido):
    return alternar_graficas(contenido, ["Por fuente", "Por tópico"])


def compactar_html_precio(contenido):
    return alternar_graficas(contenido, [
        "Precio y costo", "Valor de la experiencia", "Calidad-precio"
    ])


def mostrar_visualizacion_destacada(archivo_html, clave, altura, carpeta):
    """Conserva la firma de las vistas; la altura se ajusta al contenido."""
    if carpeta is None:
        st.info("No hay un análisis activo.")
        return

    if archivo_html not in ARCHIVOS_HTML:
        st.error("Visualización no reconocida.")
        return

    carpeta = Path(carpeta).resolve()
    ruta = (carpeta / archivo_html).resolve()

    if ruta.parent != carpeta or not ruta.is_file():
        st.info("Esta visualización no está disponible en el análisis activo.")
        return

    archivo_entrada = carpeta / "comentarios_limpios.csv"
    if archivo_entrada.is_file():
        cantidad = len(pd.read_csv(archivo_entrada))
        st.caption(f"{cantidad:,} documentos analizados · Resultados exploratorios")

    st.caption("Los resultados no garantizan representatividad turística.")

    contenido = ruta.read_text(encoding="utf-8")
    if archivo_html == "dispersion_comentarios.html":
        contenido = compactar_html_mapa(contenido)
    elif archivo_html == "precio_valor_scatter.html":
        contenido = compactar_html_precio(contenido)

    st.iframe(
        contenido,
        width="stretch",
        height="content",
        alt="Visualización interactiva de DestiLMIA"
    )
    st.download_button(
        "Descargar visualización HTML",
        data=contenido.encode("utf-8"),
        file_name=archivo_html,
        mime="text/html",
        key="descarga_destacada_" + clave
    )


def main():
    st.set_page_config(page_title="DestiLMIA", layout="wide")

    from src.tema_global import aplicar_tema
    aplicar_tema()

    from src.vista_nuevo_analisis import render_nuevo_analisis

    accion = st.sidebar.radio(
        "¿Qué deseas hacer?",
        ["Explorar resultados", "Nuevo análisis"],
        key="accion_destilmia"
    )

    if accion == "Nuevo análisis":
        render_nuevo_analisis()
        return

    carpeta = seleccionar_analisis()
    render_barra_control(carpeta)
    mostrar_guia()

    seccion = st.segmented_control(
        "Navegación principal",
        SECCIONES,
        default="Panorama",
        label_visibility="collapsed",
        key="navegacion_ejecutiva"
    ) or "Panorama"

    if carpeta is None:
        st.warning("No hay un análisis completo disponible.")
        return

    tablas = cargar_tablas(carpeta)

    if seccion == "Panorama":
        render_panel_control(tablas, carpeta)
    elif seccion == "Opiniones":
        render_sentimiento_dinamico(tablas, carpeta)
    elif seccion == "Temas":
        from src.vista_temas_sentimiento import render_dashboard_temas

        render_dashboard_temas(tablas, carpeta, mostrar_visualizacion_destacada)
    elif seccion == "DMO vs usuarios":
        render_brechas_dinamica(tablas, carpeta, mostrar_visualizacion_destacada)
    elif seccion == "Precio y valor":
        render_precio_dinamica(tablas, carpeta, mostrar_visualizacion_destacada)
    elif seccion == "Atípicos":
        render_outliers_dinamica(tablas, carpeta)


if __name__ == "__main__":
    main()
