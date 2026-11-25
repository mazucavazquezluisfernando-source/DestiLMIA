#!/usr/bin/env python3
# -*- coding: utf-8 -*-



"""Análisis de DestiLMIA."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# Configurar el entorno antes de importar los modelos.
for variable in (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS", "NUMBA_NUM_THREADS"
):
    os.environ.setdefault(variable, "1")

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
for variable in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
    os.environ[variable] = "1"

import numpy as np
import pandas as pd

from src.entrada_cli import leer_csv, preparar_entrada
from src.ngramas_outliers import tokenizar, analizar_ngramas
from src.embeddings_cli import generar_embeddings, MODELO
from src.cache_embeddings import guardar_metadatos
from src.outliers_cli import detectar_outliers
from src.alineacion_cli import calcular_alineacion
from src.sentimientos_cli import analizar_sentimientos
from src.reporte_sentimientos_cli import resumir_sentimientos
from src.topicos_cli import detectar_topicos, MIN_DOCUMENTOS
from src.scatter_comentarios_cli import generar_scatter_comentarios
from src.scatter_sentimiento_cli import generar_scatter_sentimiento
from src.distribuciones_cli import generar_distribuciones
from src.precio_valor_cli import analizar_precio_valor, comparar_precio_universos
from src.scatter_precio_valor_cli import generar_scatter_precio_valor
from src.resumen_tematico_cli import resumir_comunidades
from src.comparacion_tematica_cli import comparar_comunidades
from src.brechas_tematicas_cli import (
    construir_reporte_brechas, comparar_presencia_tematica
)


def obtener_argumentos():
    parser = argparse.ArgumentParser(description="DestiLMIA: análisis de imagen turística")
    for argumento in ("csv", "texto", "fuente", "dmo", "titulo"):
        parser.add_argument(f"--{argumento}", required=True)
    parser.add_argument("--idioma", required=True, choices=["es", "en"],
                        help="Idioma offline de respaldo para la detección automática.")
    parser.add_argument("--paleta", required=True,
                        choices=["viridis", "cividis", "plasma", "inferno"])
    return parser.parse_args()


def validar_entrada(args):
    ruta = Path(args.csv)
    if not ruta.is_file():
        raise ValueError(f"No existe el CSV: {ruta}")
    if not args.titulo.strip():
        raise ValueError("El título no puede estar vacío.")

    df = preparar_entrada(leer_csv(ruta), args.texto, args.fuente, args.dmo)
    if len(df) < 2:
        raise ValueError("Se requieren al menos dos documentos válidos.")

    fuentes = df["fuente_entrada"]
    es_dmo = fuentes.eq(args.dmo.strip())
    print("DestiLMIA - Validacion inicial")
    print("Documentos:", len(df))
    print("Documentos DMO:", int(es_dmo.sum()))
    print("Documentos percibidos:", int((~es_dmo & fuentes.notna() & fuentes.ne("")).sum()))
    print("Validacion completada correctamente")
    return df.reset_index(drop=True)


def guardar_csv(tabla, carpeta, nombre):
    tabla.to_csv(carpeta / nombre, index=False, encoding="utf-8")


def crear_carpeta():
    base = Path("resultados/cli")
    base.mkdir(parents=True, exist_ok=True)
    numeros = [int(p.name.rsplit("_", 1)[-1]) for p in base.glob("ejecucion_*")
               if p.is_dir() and p.name.rsplit("_", 1)[-1].isdigit()]
    numero = max(numeros, default=0) + 1
    while True:
        carpeta = base / f"ejecucion_{numero:03d}"
        try:
            carpeta.mkdir()
            return carpeta
        except FileExistsError:
            numero += 1


def generar_vectores(df, carpeta):
    textos = df["texto_limpio"].tolist()
    print("\nGenerando embeddings con modelo local...")
    vectores = generar_embeddings(textos)
    if (not isinstance(vectores, np.ndarray) or vectores.ndim != 2
            or vectores.shape[0] != len(df) or vectores.shape[1] == 0
            or not np.issubdtype(vectores.dtype, np.floating)
            or not np.isfinite(vectores).all()):
        raise ValueError("Embeddings inválidos o incompatibles con el corpus.")
    np.save(carpeta / "embeddings.npy", vectores, allow_pickle=False)
    guardar_metadatos(carpeta / "embeddings_metadatos.json", textos, MODELO, vectores.shape[1])
    print("\nEMBEDDINGS COMPLETADOS")
    print("Dimensiones:", vectores.shape)
    return vectores


def procesar_outliers(df, vectores, carpeta, args):
    if len(df) >= 3:
        resultado = detectar_outliers(vectores)
    else:
        resultado = {
            "es_outlier": np.zeros(len(df), dtype=bool),
            "puntuacion_anomalia": np.full(len(df), np.nan),
            "metodo": "no_evaluado", "vecinos": None,
            "multiplicador": None, "mediana": None, "mad": None,
            "umbral": None, "proporcion_atipicos": 0.0
        }
    mascara = np.asarray(resultado["es_outlier"])
    puntuaciones = np.asarray(resultado["puntuacion_anomalia"])
    if mascara.shape != (len(df),) or mascara.dtype != bool or puntuaciones.shape != (len(df),):
        raise ValueError("Resultados de outliers incompatibles con el corpus.")

    datos = df.assign(es_outlier=mascara, puntuacion_anomalia=puntuaciones)
    atipicos = datos.loc[mascara].copy()
    normales = datos.loc[~mascara].copy()
    if normales.empty:
        raise ValueError("No quedaron documentos normales para analizar.")
    guardar_csv(atipicos, carpeta, "outliers.csv")
    guardar_csv(normales, carpeta, "documentos_normales.csv")
    print("\nDETECCION DE OUTLIERS COMPLETADA")
    print("Documentos atipicos:", len(atipicos))
    print("Documentos normales:", len(normales))

    alineacion = calcular_alineacion(normales, vectores[normales.index.to_numpy(dtype=int)],
                                    columna_fuente=args.fuente, etiqueta_dmo=args.dmo)
    guardar_csv(alineacion, carpeta, "alineacion_semantica.csv")
    print("\nALINEACION SEMANTICA COMPLETADA")
    ngramas = analizar_ngramas(atipicos["texto_lexico"].tolist(), idioma=args.idioma, bilingue=True)
    guardar_csv(ngramas, carpeta, "ngramas_outliers.csv")
    print("\nANALISIS DE N-GRAMAS COMPLETADO")
    return datos, normales, resultado


def procesar_sentimientos(normales, carpeta, args):
    predicciones = analizar_sentimientos(normales["texto_limpio"].tolist(), lote=16)
    requeridas = {"sentimiento", "prob_positivo", "prob_negativo"}
    if len(predicciones) != len(normales) or not requeridas.issubset(predicciones.columns):
        raise ValueError("Predicciones de sentimiento incompatibles con el corpus.")
    if (not predicciones["sentimiento"].isin(["positivo", "neutral", "negativo"]).all()
            or not np.isfinite(predicciones[["prob_positivo", "prob_negativo"]].to_numpy(dtype=float)).all()):
        raise ValueError("Predicciones de sentimiento inválidas.")

    datos = normales.copy()
    for columna in predicciones.columns:
        datos[columna] = predicciones[columna].to_numpy()
    datos["polaridad"] = datos["sentimiento"].where(
        datos["sentimiento"].isin(["positivo", "negativo"]), "sin_polaridad")
    datos["polaridad_definida"] = datos["polaridad"].isin(["positivo", "negativo"])
    diferencia = datos["prob_positivo"] - datos["prob_negativo"]
    datos["diferencia_probabilidades"] = diferencia
    datos["polaridad_binaria"] = diferencia.ge(0).map({True: "positivo", False: "negativo"})
    datos["binaria_derivada_de_neutral"] = datos["sentimiento"].eq("neutral")
    guardar_csv(datos, carpeta, "sentimientos.csv")
    print("\nANALISIS DE SENTIMIENTOS COMPLETADO")
    por_fuente, comparacion = resumir_sentimientos(
        datos=datos, columna_fuente=args.fuente, etiqueta_dmo=args.dmo)
    guardar_csv(por_fuente, carpeta, "sentimientos_por_fuente.csv")
    guardar_csv(comparacion, carpeta, "comparacion_sentimientos_dmo_usuarios.csv")
    return datos


def procesar_topicos(sentimientos, vectores, carpeta, args):
    indices = sentimientos.index.to_numpy(dtype=int)
    vectores_topicos = vectores[indices]
    comunidades = detectar_topicos(vectores_topicos)
    if len(comunidades) != len(sentimientos):
        raise ValueError("Número de tópicos incompatible con el corpus.")
    topicos = sentimientos.reset_index(drop=True)
    topicos["indice_original"] = indices
    topicos["topico"] = comunidades["topico"].to_numpy()
    topicos["estado_topico"] = comunidades["estado"].to_numpy()
    guardar_csv(topicos, carpeta, "topicos.csv")

    particiones, palabras, representativos = [], [], []
    for sentimiento in ("positivo", "negativo"):
        posiciones = np.flatnonzero(topicos["polaridad_binaria"].eq(sentimiento).to_numpy())
        if not len(posiciones):
            continue
        grupo = topicos.iloc[posiciones].copy()
        if len(grupo) < MIN_DOCUMENTOS:
            grupo["topico_sentimiento"] = -1
            grupo["metodo_sentimiento"] = "frecuencias_muestra_pequena"
        else:
            resultado = detectar_topicos(vectores_topicos[posiciones], minimo=MIN_DOCUMENTOS)
            grupo["topico_sentimiento"] = resultado["topico"].to_numpy()
            grupo["metodo_sentimiento"] = "leiden_independiente"
        particiones.append(grupo)

        for topico, comunidad in grupo.groupby("topico_sentimiento"):
            for fuente, subgrupo in comunidad.groupby(args.fuente):
                frecuencias = analizar_ngramas(subgrupo["texto_lexico"].tolist(),
                                              idioma=args.idioma, bilingue=True)
                for _, fila in frecuencias.iterrows():
                    palabras.append({
                        "sentimiento": sentimiento, "topico": int(topico), "fuente": fuente,
                        "tipo": fila["tipo"], "expresion": fila["expresion"],
                        "frecuencia": int(fila["frecuencia"])
                    })

            # Documento más cercano al centroide de cada comunidad.
            matriz = vectores_topicos[comunidad.index.to_numpy(dtype=int)].astype(float)
            centro = matriz.mean(axis=0)
            similitudes = (matriz @ centro) / (
                np.linalg.norm(matriz, axis=1) * np.linalg.norm(centro) + 1e-12)
            elegido = comunidad.iloc[int(np.argmax(similitudes))]
            representativos.append({
                "sentimiento": sentimiento, "topico": int(topico),
                "metodo": elegido["metodo_sentimiento"],
                "indice_original": int(elegido["indice_original"]),
                "fuente": elegido[args.fuente], "similitud_centroide": float(np.max(similitudes)),
                "texto": elegido[args.texto]
            })

    columnas = list(topicos.columns) + ["topico_sentimiento", "metodo_sentimiento"]
    particiones = (pd.concat(particiones, ignore_index=True) if particiones
                   else pd.DataFrame(columns=columnas))
    guardar_csv(particiones, carpeta, "topicos_por_sentimiento.csv")
    guardar_csv(pd.DataFrame(palabras, columns=[
        "sentimiento", "topico", "fuente", "tipo", "expresion", "frecuencia"
    ]), carpeta, "palabras_clave_topicos.csv")
    guardar_csv(pd.DataFrame(representativos, columns=[
        "sentimiento", "topico", "metodo", "indice_original", "fuente",
        "similitud_centroide", "texto"
    ]), carpeta, "comentarios_representativos_topicos.csv")
    print("\nTOPICOS POR SENTIMIENTO COMPLETADOS")
    generar_scatter_sentimiento(datos=particiones.copy(), embeddings=vectores,
                               columna_fuente=args.fuente, columna_texto=args.texto,
                               ruta=carpeta / "topicos_por_sentimiento_scatter.html",
                               titulo=args.titulo, paleta=args.paleta, etiqueta_dmo=args.dmo)
    print("\nSCATTER DE TOPICOS POR SENTIMIENTO COMPLETADO")
    return topicos


def generar_visualizaciones(datos, sentimientos, topicos, vectores, carpeta, args):
    generar_distribuciones(datos=topicos, columna_fuente=args.fuente, etiqueta_dmo=args.dmo,
                           ruta=carpeta / "distribuciones_dmo_usuarios.html",
                           titulo=args.titulo, paleta=args.paleta)
    print("\nDISTRIBUCIONES DMO-USUARIOS COMPLETADAS")
    generar_scatter_comentarios(datos, sentimientos, topicos, vectores,
                               columna_fuente=args.fuente, columna_texto=args.texto,
                               ruta=carpeta / "dispersion_comentarios.html",
                               titulo=args.titulo, paleta=args.paleta, etiqueta_dmo=args.dmo)
    print("\nSCATTER INTERACTIVO COMPLETADO")


def procesar_precio(datos, sentimientos, vectores, carpeta, args):
    detalle, resumen, cercanos, distribucion = analizar_precio_valor(
        documentos=datos, sentimientos=sentimientos, embeddings=vectores,
        generar_embeddings=generar_embeddings, columna_fuente=args.fuente,
        columna_texto=args.texto, etiqueta_dmo=args.dmo)
    guardar_csv(detalle, carpeta, "precio_valor_similitudes.csv")
    guardar_csv(resumen, carpeta, "precio_valor_resumen_fuentes.csv")
    guardar_csv(cercanos, carpeta, "precio_valor_cinco_cercanos.csv")
    guardar_csv(distribucion, carpeta, "precio_valor_distribucion_candidatos.csv")
    comparacion, ejemplos = comparar_precio_universos(detalle, args.dmo)
    guardar_csv(comparacion, carpeta, "precio_valor_dmo_usuarios.csv")
    guardar_csv(ejemplos, carpeta, "precio_valor_contexto_universos.csv")
    print("\nANALISIS SEMANTICO DE PRECIO Y VALOR COMPLETADO")
    print("Nota: las similitudes no son etiquetas economicas validadas.")
    generar_scatter_precio_valor(detalle, cercanos, carpeta / "precio_valor_scatter.html",
                                titulo=args.titulo, paleta=args.paleta)
    print("\nSCATTER DE PRECIO Y VALOR COMPLETADO")


def procesar_brechas(topicos, vectores, carpeta, args):
    print("\nMODELADO DE TOPICOS COMPLETADO")
    universos, fuentes = resumir_comunidades(datos=topicos, columna_fuente=args.fuente,
                                            columna_texto=args.texto, etiqueta_dmo=args.dmo,
                                            idioma=args.idioma)
    guardar_csv(universos, carpeta, "resumen_temas_dmo_usuarios.csv")
    guardar_csv(fuentes, carpeta, "resumen_temas_por_fuente.csv")
    guardar_csv(comparar_presencia_tematica(universos), carpeta, "presencia_tematica_dmo_usuarios.csv")
    comparacion = comparar_comunidades(datos=topicos, embeddings=vectores,
                                       columna_fuente=args.fuente, etiqueta_dmo=args.dmo)
    guardar_csv(comparacion, carpeta, "comparacion_tematica_dmo.csv")
    guardar_csv(construir_reporte_brechas(universos, comparacion), carpeta,
                "brechas_tematicas_dmo_usuarios.csv")
    print("\nCOMPARACION TEMATICA DMO-USUARIOS COMPLETADA")


def registrar_metadatos(args, df, topicos, outliers, carpeta, originales):
    metadatos = {
        "fecha_analisis": datetime.now().astimezone().isoformat(timespec="seconds"),
        "titulo": args.titulo, "archivo_entrada": str(args.csv),
        "etiqueta_dmo": args.dmo, "columna_texto_original": originales[0],
        "columna_fuente_original": originales[1], "columna_texto": args.texto,
        "columna_fuente": args.fuente, "idioma": args.idioma, "paleta": args.paleta,
        "documentos_entrada": len(df), "documentos_topicos": len(topicos),
        "outliers_evaluados": len(df) >= 3,
        "metodo_outliers": outliers["metodo"], "vecinos_outliers": outliers["vecinos"],
        "multiplicador_outliers": outliers["multiplicador"], "mediana_outliers": outliers["mediana"],
        "mad_outliers": outliers["mad"], "umbral_outliers": outliers["umbral"],
        "proporcion_atipicos": outliers["proporcion_atipicos"],
        "procedencia_declarada": os.environ.get("DESTILMIA_PROCEDENCIA", "No especificada"),
        "estado": "finalizado"
    }
    temporal = carpeta / "metadatos_analisis.tmp"
    temporal.write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(carpeta / "metadatos_analisis.json")
    print("Fecha del analisis:", metadatos["fecha_analisis"])


def main():
    args = obtener_argumentos()
    df = validar_entrada(args)
    originales = (args.texto, args.fuente)
    args.texto, args.fuente = "texto_entrada", "fuente_entrada"
    args.dmo = args.dmo.strip()
    df["texto_lexico"] = df["texto_limpio"].map(
        lambda texto: " ".join(tokenizar(texto, idioma=args.idioma, bilingue=True, lematizar=True)))
    carpeta = crear_carpeta()
    guardar_csv(df, carpeta, "comentarios_limpios.csv")
    print("\nPREPROCESAMIENTO COMPLETADO")
    print("Documentos procesados:", len(df))
    print("Textos vacios:", int(df["texto_limpio"].eq("").sum()))
    print("Archivo generado:", carpeta / "comentarios_limpios.csv")

    vectores = generar_vectores(df, carpeta)
    datos, normales, outliers = procesar_outliers(df, vectores, carpeta, args)
    sentimientos = procesar_sentimientos(normales, carpeta, args)
    topicos = procesar_topicos(sentimientos, vectores, carpeta, args)
    generar_visualizaciones(datos, sentimientos, topicos, vectores, carpeta, args)
    procesar_precio(datos, sentimientos, vectores, carpeta, args)
    procesar_brechas(topicos, vectores, carpeta, args)
    registrar_metadatos(args, df, topicos, outliers, carpeta, originales)


if __name__ == "__main__":
    main()
