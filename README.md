# DestiLMIA

Análisis comparativo de la imagen turística proyectada por una DMO y la imagen percibida en fuentes digitales. Herramienta local desarrollada en Python para el proyecto final de Visualización de Datos.

## Instalación

El proyecto se ha probado con Python 3.14.7 en macOS. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

La instalación inicial y descarga de pesos necesitan Internet. El análisis posterior no utiliza APIs externas ni requiere conexión. Descarga una sola vez los modelos de spaCy y los dos modelos neuronales:

```bash
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
python - <<'PY'
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
nombre = 'cardiffnlp/twitter-xlm-roberta-base-sentiment'
AutoTokenizer.from_pretrained(nombre, fix_mistral_regex=True)
AutoModelForSequenceClassification.from_pretrained(nombre)
PY
```

Los modelos permanecen en la caché local. Si falta alguno, el análisis debe detenerse con error; no intenta descargar pesos durante el análisis. En Windows, ejecuta las líneas Python del bloque anterior en un archivo `.py`. Se requiere espacio y memoria suficientes para los modelos y los corpus. Las dependencias nativas (FAISS, igraph, PyTorch) deben disponer de versiones compatibles con la plataforma. La instalación limpia en cada plataforma debe verificarse antes de prometer compatibilidad.

## Entrada y ejecución obligatoria desde terminal

CSV UTF-8 con encabezados y al menos una fila textual de la DMO y otra de una fuente percibida. Se permiten columnas adicionales; el análisis conserva el texto seleccionado y la etiqueta de fuente, sin modificar el CSV original. Los espacios exteriores de las fuentes se normalizan. No se aceptan textos vacíos tras la limpieza ni fuentes vacías. Las etiquetas de fuente distinguen mayúsculas de minúsculas. El ejemplo incluido es **sintético** y no describe la realidad turística de Guanajuato.

```bash
python main.py --help
python main.py \
  --csv data/pruebas/guanajuato_sintetico_100.csv \
  --texto resena \
  --fuente plataforma \
  --dmo oficial_gto \
  --idioma es \
  --titulo 'Guanajuato - prueba sintetica' \
  --paleta cividis
```

| Parámetro obligatorio | Función |
|---|---|
| `--csv` | Ruta del CSV |
| `--texto` | Nombre exacto de la columna de texto |
| `--fuente` | Nombre exacto de la columna de fuente |
| `--dmo` | Etiqueta de la fuente oficial |
| `--idioma` | `es` o `en`: idioma predeterminado del procesamiento bilingüe offline |
| `--titulo` | Título de las visualizaciones y metadatos |
| `--paleta` | `viridis`, `cividis`, `plasma`, `inferno`; cividis es una opción accesible |

## Interfaz opcional

```bash
python -m streamlit run app.py
```

En Nuevo análisis, carga el CSV, identifica columnas y DMO, declara la procedencia y ejecuta. El estado se actualiza automáticamente durante el procesamiento. Al finalizar, utiliza el botón Ver resultados. En Explorar resultados, selecciona un análisis. La aplicación es local; no se ha diseñado como servicio multiusuario público. Los archivos de entrada y resultados pueden contener texto sensible; no deben publicarse sin autorización.

### Idiomas y restricciones

- Idiomas soportados en modo offline: español (es) e inglés (en).
- La interfaz Streamlit admite archivos CSV de hasta 30 MB.
- El CLI no impone ese límite explícito.
- La capacidad de procesamiento depende de la memoria y los recursos del equipo.
- La instalación inicial requiere Internet; el análisis utiliza modelos locales.

## Metodología

1. Limpieza de URLs, teléfonos y espacios. El texto natural conserva puntuación y números relevantes para los modelos. Una segunda representación léxica utiliza Lingua para detectar español o inglés, spaCy para lematizar y stopwords bilingües. El parámetro --idioma establece el idioma predeterminado cuando la detección no es concluyente.
2. MiniLM multilingüe: un embedding por documento, promedio de fragmentos para evitar truncar entradas largas.
3. Detección de aislamiento semántico mediante la similitud coseno promedio de hasta cinco vecinos más cercanos, excluyendo el propio documento. Se utiliza un umbral global robusto: mediana menos 3 × 1.4826 × MAD, con tolerancia numérica de 1e-6. No se impone una proporción fija de atípicos. Los atípicos se analizan mediante unigramas, bigramas y trigramas. Con dos documentos no se evalúan anomalías. El aislamiento semántico no equivale a irrelevancia turística y puede verse afectado por el desequilibrio entre fuentes.
4. XLM-R de sentimientos: positivo, negativo y neutral originales. Para el requisito binario se compara la probabilidad positiva frente a la negativa (empate a positivo); se identifica si procede de neutral. Una etiqueta binaria derivada no es evidencia de una opinión polarizada. El clasificador limita la entrada a 512 tokens.
5. UMAP, grafo de vecinos y Leiden: comunidades generales y comunidades independientes para cada polaridad. Todos los textos normales se incluyen. Si hay menos de 15 textos en una partición, se reportan frecuencias en lugar de asignar tópicos. Las palabras se cuentan por fuente y se elige un texto representativo cercano al centroide.
6. Alineación: coseno de centroides de embeddings normalizados para la DMO frente a todas las fuentes y por fuente. Distribución temática, tono, términos y ejemplos por segmento; diferencias en puntos porcentuales y comparación de centroides. Si no hay textos normales de un universo, el coseno no es calculable.
7. Visualizaciones interactivas de Plotly sin conexión a Internet, PCA bidimensional, color y forma, texto al pasar el cursor. La proyección es exploratoria y no conserva todas las distancias del espacio original.
8. Precio, costo, valor de la experiencia y relación calidad-precio: máxima similitud coseno frente a frases de referencia para cada concepto, cinco textos cercanos, candidatos con evidencia léxica y cribado semántico relativo (percentil 90 del corpus por concepto, incluye empates), comparación de frecuencia y tono original por universo y ejemplos. El percentil es una regla exploratoria de selección, no un umbral validado de relevancia. No es un clasificador económico validado. Los atípicos se incluyen en la similitud de precio pero su sentimiento no se evalúa.

Las comunidades no son categorías turísticas confirmadas. Una ausencia de comunidad compartida no prueba una brecha temática. La similitud no mide satisfacción ni porcentaje de acuerdo. La representatividad depende de la calidad del CSV. El análisis binario y la detección de anomalías requieren revisión humana. El tiempo de procesamiento aumenta con el tamaño del corpus.

## Resultados

Cada ejecución crea `resultados/cli/ejecucion_NNN/` sin sobrescribir anteriores. El archivo `metadatos_analisis.json` registra finalización, fecha, título, columnas originales, etiqueta DMO, idioma y paleta. Entre las salidas principales:

| Resultado | Archivo |
|---|---|
| Limpieza / normales / anomalías | `comentarios_limpios.csv`, `documentos_normales.csv`, `outliers.csv`, `ngramas_outliers.csv` |
| Sentimientos | `sentimientos.csv`, `sentimientos_por_fuente.csv`, `comparacion_sentimientos_dmo_usuarios.csv` |
| Tópicos | `topicos.csv`, `topicos_por_sentimiento.csv`, `palabras_clave_topicos.csv`, `comentarios_representativos_topicos.csv` |
| Comparación | `alineacion_semantica.csv`, `resumen_temas_dmo_usuarios.csv`, `resumen_temas_por_fuente.csv`, `comparacion_tematica_dmo.csv`, `brechas_tematicas_dmo_usuarios.csv`, `presencia_tematica_dmo_usuarios.csv` |
| Precio y valor | `precio_valor_similitudes.csv`, `precio_valor_resumen_fuentes.csv`, `precio_valor_cinco_cercanos.csv`, `precio_valor_distribucion_candidatos.csv`, `precio_valor_dmo_usuarios.csv`, `precio_valor_contexto_universos.csv` |
| HTML interactivo | `dispersion_comentarios.html`, `topicos_por_sentimiento_scatter.html`, `distribuciones_dmo_usuarios.html`, `precio_valor_scatter.html` |

## Estructura

- `main.py`: CLI y orquestación del análisis.
- `src/`: limpieza, procesamiento, modelos, comparaciones y vistas.
- `app.py`: interfaz Streamlit.
- `data/pruebas/guanajuato_sintetico_100.csv`: ejemplo sintético.
- `tests/`: comprobaciones de lógica e integración.
- `requirements.txt`: dependencias de Python.

Los pesos, entornos virtuales, corpus reales y resultados generados se excluyen mediante `.gitignore`.
