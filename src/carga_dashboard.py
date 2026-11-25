import pandas as pd
import json


TABLAS = {'entrada': 'comentarios_limpios.csv', 'topicos': 'topicos.csv', 'sentimientos': 'sentimientos_por_fuente.csv', 'sentimientos_detalle': 'sentimientos.csv', 'comparacion_sentimientos': 'comparacion_sentimientos_dmo_usuarios.csv', 'topicos_polaridad': 'topicos_por_sentimiento.csv', 'palabras_clave': 'palabras_clave_topicos.csv', 'representativos': 'comentarios_representativos_topicos.csv', 'alineacion': 'alineacion_semantica.csv', 'brechas': 'brechas_tematicas_dmo_usuarios.csv', 'resumen_universos': 'resumen_temas_dmo_usuarios.csv', 'resumen_fuentes': 'resumen_temas_por_fuente.csv', 'comparacion_tematica': 'comparacion_tematica_dmo.csv', 'precio': 'precio_valor_resumen_fuentes.csv', 'precio_detalle': 'precio_valor_similitudes.csv', 'precio_cercanos': 'precio_valor_cinco_cercanos.csv', 'outliers': 'outliers.csv', 'ngramas_outliers': 'ngramas_outliers.csv'}

ARCHIVOS_REQUERIDOS = tuple(TABLAS.values())


def analisis_completo(carpeta):
    try:
        meta = json.loads((carpeta / "metadatos_analisis.json").read_text(encoding="utf-8"))
        return isinstance(meta, dict) and meta.get("estado") == "finalizado" and all((carpeta / archivo).is_file() for archivo in ARCHIVOS_REQUERIDOS)
    except (OSError, ValueError):
        return False


def cargar_tablas(carpeta):

    if carpeta is None:
        raise ValueError("No existe un análisis completo.")

    meta = json.loads((carpeta / "metadatos_analisis.json").read_text(encoding="utf-8"))
    columnas_textuales = {
        "fuente", "fuente_entrada", "fuente_percibida",
        "segmento", "texto", "texto_entrada",
        "texto_limpio", "texto_lexico", "expresion",
        "terminos", "ejemplo_lexico", "terminos_usuarios",
        "ejemplo_usuarios", "terminos_dmo_cercana",
        "frase_mas_cercana",
    }

    columnas_textuales.update(
        meta[k]
        for k in ("columna_texto", "columna_fuente")
        if k in meta
    )

    if "columna_fuente" not in meta:
        columnas_textuales.add(
            pd.read_csv(
                carpeta / TABLAS["sentimientos"],
                nrows=0
            ).columns[0]
        )

        columnas_textuales.update(
            pd.read_csv(
                carpeta / TABLAS["entrada"],
                nrows=0
            ).columns
        )

    tablas = {}

    for clave, archivo in TABLAS.items():
        ruta = carpeta / archivo
        columnas = pd.read_csv(ruta, nrows=0).columns

        tablas[clave] = pd.read_csv(
            ruta,
            dtype={
                c: str for c in columnas
                if c in columnas_textuales
            },
            keep_default_na=False,
            na_values={
                c: [""] for c in columnas
                if c not in columnas_textuales
            },
        )
    tablas["metadatos"] = meta
    return tablas
