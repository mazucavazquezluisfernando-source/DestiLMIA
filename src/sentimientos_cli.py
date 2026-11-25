import numpy as np
import pandas as pd


MODELO_SENTIMIENTOS = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

ETIQUETAS = {
    "negative": "negativo",
    "neutral": "neutral",
    "positive": "positivo"
}


def cargar_clasificador():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

    tokenizador = AutoTokenizer.from_pretrained(
        MODELO_SENTIMIENTOS,
        local_files_only=True,
        fix_mistral_regex=True
    )

    modelo = AutoModelForSequenceClassification.from_pretrained(
        MODELO_SENTIMIENTOS,
        local_files_only=True
    )

    return pipeline(
        "text-classification",
        model=modelo,
        tokenizer=tokenizador,
        device=-1
    )


def analizar_sentimientos(textos, clasificador=None, lote=16):
    if isinstance(textos, str):
        raise ValueError("Se requiere una colección de documentos")

    textos = list(textos)

    columnas = [
        "sentimiento",
        "confianza_sentimiento",
        "prob_negativo",
        "prob_neutral",
        "prob_positivo"
    ]

    if not isinstance(lote, (int, np.integer)) or lote < 1:
        raise ValueError("El tamaño del lote debe ser un entero positivo")

    if not textos:
        return pd.DataFrame(columns=columnas)

    if any(not isinstance(t, str) or not t.strip() for t in textos):
        raise ValueError("Hay textos vacíos o inválidos")

    if clasificador is None:
        clasificador = cargar_clasificador()

    resultados = []

    for inicio in range(0, len(textos), lote):
        fragmento = textos[inicio:inicio + lote]

        predicciones = clasificador(
            fragmento,
            truncation=True,
            max_length=512,
            top_k=None,
            batch_size=lote
        )

        if len(predicciones) != len(fragmento):
            raise ValueError("La cantidad de predicciones no coincide")

        for prediccion in predicciones:
            probabilidades = {
                p["label"].lower(): float(p["score"])
                for p in prediccion
            }

            if len(prediccion) != 3 or set(probabilidades) != set(ETIQUETAS):
                raise ValueError("El modelo devolvió etiquetas inesperadas")

            valores = np.array(list(probabilidades.values()), dtype=float)

            if (not np.isfinite(valores).all()
                    or np.any((valores < 0) | (valores > 1))
                    or not np.isclose(valores.sum(), 1.0, atol=1e-4, rtol=0)):
                raise ValueError("El modelo devolvió probabilidades inválidas")

            etiqueta = max(probabilidades, key=probabilidades.get)

            resultados.append({
                "sentimiento": ETIQUETAS[etiqueta],
                "confianza_sentimiento": probabilidades[etiqueta],
                "prob_negativo": probabilidades["negative"],
                "prob_neutral": probabilidades["neutral"],
                "prob_positivo": probabilidades["positive"]
            })

        if (inicio // lote + 1) % 25 == 0 or len(resultados) == len(textos):
            print(f"Sentimientos: {len(resultados)}/{len(textos)}", flush=True)

    return pd.DataFrame(resultados, columns=columnas)
