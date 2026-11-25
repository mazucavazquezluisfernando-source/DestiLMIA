import pandas as pd

from src.preprocess import limpiar_ligero


def leer_csv(ruta):
    return pd.read_csv(
        ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )


def es_columna_textual(serie):
    valores = serie.dropna().astype(str).str.strip()
    valores = valores[valores.ne("")]
    return not valores.empty and not pd.to_numeric(
        valores, errors="coerce"
    ).notna().all()


def preparar_entrada(datos, texto, fuente, dmo):
    if texto == fuente or texto not in datos or fuente not in datos:
        raise ValueError("Selecciona dos columnas existentes y distintas.")

    if datos.empty or not es_columna_textual(datos[texto]):
        raise ValueError("El CSV no contiene comentarios textuales válidos.")

    salida = datos[[texto, fuente]].copy().reset_index(drop=True)
    salida.columns = ["texto_entrada", "fuente_entrada"]

    salida["fuente_entrada"] = (
        salida["fuente_entrada"].fillna("").astype(str).str.strip()
    )

    salida["texto_limpio"] = (
        salida["texto_entrada"].fillna("").astype(str).map(limpiar_ligero)
    )

    invalidos = salida["texto_limpio"].eq("") | salida["fuente_entrada"].eq("")

    if invalidos.any():
        raise ValueError(
            f"{invalidos.sum()} registros sin texto válido o fuente después de limpiar."
        )

    oficial = salida["fuente_entrada"].eq(dmo.strip())

    if not oficial.any() or oficial.all():
        raise ValueError("Se requiere al menos un comentario DMO y uno percibido.")

    return salida
