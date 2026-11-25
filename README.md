# DestiLMIA

Análisis comparativo de la imagen turística proyectada por una DMO y la imagen percibida. Proyecto final de Visualización de la información.

## Sobre el proyecto

La idea de este proyecto surge de comparar la manera en que un destino turístico se promociona con lo que las personas realmente comentan sobre él.

Una DMO (Destination Management Organization) puede destacar ciertos lugares, actividades o experiencias de un destino, pero esto no significa que los visitantes tengan necesariamente la misma percepción.

Con DestiLMIA busco analizar ambas perspectivas a partir de textos provenientes de distintas fuentes. Me interesa conocer qué temas tienen en común, cuáles son sus diferencias, qué sentimientos expresan los usuarios y cómo hablan sobre los precios y el valor de sus experiencias.

Para trabajar con estos datos utilicé herramientas de procesamiento del lenguaje natural, aprendizaje automático y visualización de la información.

Desarrollé el proyecto en Python y agregué una interfaz en Streamlit para facilitar la exploración de los resultados. También es posible realizar todo el análisis directamente desde la terminal.

## Instalación

Trabajé con Python 3.14.7 en macOS. Recomiendo crear un entorno virtual para instalar las bibliotecas del proyecto sin afectar las que ya se tengan instaladas.

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Todas las bibliotecas necesarias están en el archivo `requirements.txt`.

### Descarga de los modelos

Una de las cosas que busqué fue que el análisis pudiera realizarse sin depender de una conexión a Internet ni de servicios externos.

Para esto es necesario descargar los modelos una primera vez.

```bash
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
```

Después, los modelos que utilizo para generar embeddings y analizar sentimientos:

```bash
python - <<'PY'
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification

SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

nombre = 'cardiffnlp/twitter-xlm-roberta-base-sentiment'

AutoTokenizer.from_pretrained(nombre, fix_mistral_regex=True)
AutoModelForSequenceClassification.from_pretrained(nombre)
PY
```

Una vez descargados, los modelos se guardan localmente y no es necesario volver a descargarlos para cada análisis.

Si falta alguno, el programa muestra un error en lugar de intentar descargarlo durante el análisis.

En Windows se pueden colocar las instrucciones de Python del último bloque en un archivo `.py` y ejecutarlo desde la terminal.

La instalación y el tiempo de procesamiento también dependen del equipo que se utilice. Hasta el momento he trabajado con macOS, por lo que no puedo asegurar que todas las bibliotecas funcionen de la misma manera en otros sistemas operativos sin probarlas antes.

## Cómo utilizar DestiLMIA

Para realizar un análisis necesito un archivo CSV que contenga los textos y una columna que indique de qué fuente proviene cada uno.

No es necesario que las columnas tengan un nombre específico, ya que el programa permite seleccionarlas al momento de ejecutar el análisis.

El archivo debe estar en formato UTF-8, tener encabezados y contener al menos un texto de la DMO y otro de alguna fuente de usuarios.

Puede tener otras columnas, aunque para el análisis se utilizan principalmente el texto y la fuente.

El programa elimina los espacios innecesarios alrededor de los nombres de las fuentes. No acepta fuentes vacías ni textos que queden vacíos después de la limpieza. También distingue entre mayúsculas y minúsculas en los nombres de las fuentes.

El archivo original no se modifica.

### Desde la terminal

Para consultar los parámetros disponibles:

```bash
python main.py --help
```

Incluí un CSV sintético de Guanajuato para que sea posible probar el proyecto sin tener que conseguir otro conjunto de datos.

```bash
python main.py \
  --csv data/pruebas/guanajuato_sintetico_100.csv \
  --texto resena \
  --fuente plataforma \
  --dmo oficial_gto \
  --idioma es \
  --titulo 'Guanajuato - prueba sintetica' \
  --paleta cividis
```

Los datos de este ejemplo son ficticios y no representan la percepción real de los turistas que visitan Guanajuato.

Estos son los siete parámetros necesarios para realizar un análisis:

| Parámetro | Para qué sirve |
|---|---|
| `--csv` | Indica dónde se encuentra el archivo CSV. |
| `--texto` | Nombre de la columna que contiene los textos. |
| `--fuente` | Nombre de la columna que identifica las fuentes. |
| `--dmo` | Nombre con el que aparece la fuente oficial en el CSV. |
| `--idioma` | Idioma predeterminado del análisis: `es` o `en`. |
| `--titulo` | Nombre que quiero darle al análisis. |
| `--paleta` | Colores que se utilizarán en las visualizaciones. |

Las paletas disponibles son `viridis`, `cividis`, `plasma` e `inferno`. Cividis es una opción que facilita la diferenciación de colores para personas con deficiencias en la visión del color.

### Desde el dashboard

También agregué una interfaz para que sea más fácil realizar análisis y consultar los resultados sin tener que escribir todos los parámetros desde la terminal.

Para abrirla:

```bash
python -m streamlit run app.py
```

En la opción Nuevo análisis se puede cargar el CSV, seleccionar sus columnas, identificar la DMO, indicar la procedencia de los datos y configurar el análisis.

Durante el procesamiento se muestra el estado de la ejecución. Al terminar, se pueden consultar los resultados directamente desde la interfaz.

En Explorar resultados también es posible abrir análisis realizados anteriormente.

Organicé el dashboard en seis apartados:

- Panorama.
- Opiniones.
- Temas.
- DMO vs usuarios.
- Precio y valor.
- Atípicos.

El programa trabaja con textos en español e inglés.

La interfaz permite cargar archivos de hasta 30 MB. Desde la terminal no establecí ese límite, aunque la cantidad de textos que se pueden procesar depende de la memoria y los recursos disponibles.

La aplicación está pensada para utilizarse de manera local, no como un servicio público para varios usuarios al mismo tiempo.

## Cómo funciona el análisis

### Limpieza de los textos

Antes de analizar los comentarios elimino elementos como URLs, números telefónicos y espacios innecesarios.

Trabajo con dos representaciones del texto. Una conserva la puntuación y los números que pueden aportar contexto a los modelos neuronales. La otra está pensada para analizar las palabras que aparecen con mayor frecuencia.

Para esta segunda representación utilizo Lingua para detectar el idioma, spaCy para lematizar las palabras y listas de stopwords en español e inglés.

Cuando no es posible determinar el idioma con suficiente claridad, utilizo el que se indicó en el parámetro `--idioma`.

### Embeddings

Utilizo el modelo multilingüe paraphrase-multilingual-MiniLM-L12-v2 para representar cada documento mediante un vector numérico.

Esto me permite comparar textos a partir de su significado y no únicamente de las palabras que tienen en común.

Cuando un documento es demasiado largo, lo divido en fragmentos y promedio sus embeddings para obtener una sola representación del texto completo sin tener que descartar el contenido restante.

### Detección de documentos atípicos

Para identificar los documentos que se alejan del resto del corpus utilizo la similitud coseno.

Comparo cada documento con hasta cinco de sus vecinos más cercanos, sin incluir el propio documento, y calculo la similitud promedio.

Para determinar qué documentos pueden considerarse atípicos utilizo la mediana y la desviación absoluta mediana (MAD).

El umbral se obtiene restando a la mediana tres veces el MAD ajustado por el factor 1.4826, con una tolerancia numérica de 0.000001.

No establezco previamente una cantidad ni un porcentaje de documentos que deban considerarse atípicos.

Después analizo las palabras y combinaciones de palabras que aparecen en estos textos mediante unigramas, bigramas y trigramas.

Si el corpus solamente tiene dos documentos, no realizo la detección de anomalías.

Que un documento sea atípico no significa necesariamente que sea irrelevante. Puede tratarse de una experiencia diferente, de un tema poco frecuente o de un efecto producido por el desequilibrio entre las fuentes.

### Análisis de sentimientos

Para identificar el sentimiento de los comentarios utilizo el modelo twitter-xlm-roberta-base-sentiment.

El modelo devuelve probabilidades para tres categorías:

- Positivo.
- Negativo.
- Neutral.

Conservo estas categorías para conocer el sentimiento original de cada comentario.

También realizo una clasificación binaria para separar los comentarios positivos y negativos. Para esto comparo ambas probabilidades y selecciono la mayor. Si existe un empate, asigno la categoría positiva.

Conservo la información de los comentarios que originalmente fueron neutrales para distinguirlos de los que el modelo identificó directamente como positivos o negativos.

Esto es importante porque asignar una categoría binaria a un comentario neutral no significa que la persona haya expresado una opinión claramente positiva o negativa.

El modelo de sentimientos admite un máximo de 512 tokens por entrada.

### Identificación de temas

Para conocer los temas de los que hablan las distintas fuentes utilizo UMAP y el algoritmo Leiden.

UMAP me permite reducir la dimensionalidad de los embeddings. Después construyo un grafo a partir de las relaciones entre los documentos y utilizo Leiden para identificar comunidades.

Realizo un análisis general de los documentos normales y también un análisis independiente para los comentarios positivos y negativos.

Cuando alguno de estos grupos tiene menos de 15 documentos, prefiero mostrar las frecuencias de las palabras en lugar de formar comunidades con una cantidad tan pequeña de información.

También obtengo las palabras más frecuentes por fuente y selecciono comentarios representativos cercanos al centro de las comunidades en el análisis por sentimiento.

### Comparación entre la DMO y los usuarios

Esta es una de las partes centrales del proyecto.

Comparo la representación semántica de los textos de la DMO con la de todos los usuarios en conjunto y con cada una de las fuentes por separado.

Para esto utilizo los centroides de los embeddings normalizados y calculo su similitud coseno.

Además de la alineación semántica, comparo los temas, los sentimientos, las palabras y los comentarios representativos de cada grupo.

Las diferencias en la presencia de los temas se expresan en puntos porcentuales. Esto permite identificar temas que tienen mayor presencia en la comunicación oficial o en los comentarios de los usuarios.

Cuando alguno de los dos grupos no tiene documentos normales disponibles, no es posible calcular su alineación.

### Precio y valor

También me interesaba conocer cómo hablan las personas sobre el aspecto económico de sus experiencias.

Para esta parte trabajo con tres conceptos:

- Precio y costo.
- Valor de la experiencia.
- Relación calidad-precio.

Comparo los embeddings de los documentos con frases de referencia relacionadas con estos conceptos y utilizo la mayor similitud coseno obtenida para cada uno.

Después identifico los cinco textos más cercanos a cada concepto, o todos los disponibles si hay menos de cinco.

Para encontrar posibles comentarios relacionados con estos temas utilizo evidencia léxica y una selección semántica basada en el percentil 90 de las similitudes del corpus, incluyendo los empates.

Comparo la frecuencia y el sentimiento original de estos comentarios entre la DMO y los usuarios, además de mostrar ejemplos para conocer su contexto.

En esta parte también incluyo los documentos atípicos, aunque estos no tienen una clasificación de sentimiento.

El objetivo no es determinar automáticamente si un destino es caro o barato. Lo que busco es encontrar textos que puedan aportar información sobre estos aspectos y facilitar su revisión.

### Visualización de la información

Utilicé Plotly y Streamlit para presentar los resultados de manera interactiva.

En los gráficos de dispersión utilizo PCA para representar los documentos en dos dimensiones.

También utilizo colores y formas para diferenciar los grupos. Al pasar el cursor sobre los puntos es posible consultar la información de los documentos.

Los gráficos generados en formato HTML pueden abrirse sin conexión a Internet.

La reducción a dos dimensiones ayuda a explorar los datos, pero no conserva todas las distancias que existen en el espacio original de los embeddings.

## Resultados

Cada vez que se realiza un análisis se crea una carpeta diferente dentro de:

```text
resultados/cli/
```

Las ejecuciones se guardan con nombres como `ejecucion_001`, `ejecucion_002` y así sucesivamente. De esta manera puedo consultar análisis anteriores sin sobrescribirlos.

También guardo un archivo llamado `metadatos_analisis.json` con la fecha de ejecución, el título, las columnas utilizadas, la DMO, el idioma, la paleta y el estado de finalización.

Entre los archivos que genera el programa se encuentran los siguientes:

| Resultado | Archivos |
|---|---|
| Limpieza y documentos atípicos | `comentarios_limpios.csv`, `documentos_normales.csv`, `outliers.csv`, `ngramas_outliers.csv` |
| Sentimientos | `sentimientos.csv`, `sentimientos_por_fuente.csv`, `comparacion_sentimientos_dmo_usuarios.csv` |
| Temas | `topicos.csv`, `topicos_por_sentimiento.csv`, `palabras_clave_topicos.csv`, `comentarios_representativos_topicos.csv` |
| Comparación entre fuentes | `alineacion_semantica.csv`, `resumen_temas_dmo_usuarios.csv`, `resumen_temas_por_fuente.csv`, `comparacion_tematica_dmo.csv`, `brechas_tematicas_dmo_usuarios.csv`, `presencia_tematica_dmo_usuarios.csv` |
| Precio y valor | `precio_valor_similitudes.csv`, `precio_valor_resumen_fuentes.csv`, `precio_valor_cinco_cercanos.csv`, `precio_valor_distribucion_candidatos.csv`, `precio_valor_dmo_usuarios.csv`, `precio_valor_contexto_universos.csv` |
| Visualizaciones | `dispersion_comentarios.html`, `topicos_por_sentimiento_scatter.html`, `distribuciones_dmo_usuarios.html`, `precio_valor_scatter.html` |

Los archivos CSV permiten consultar los datos de cada análisis y también utilizarlos en otras herramientas.

## Cosas que hay que tener en cuenta

Los resultados dependen mucho de los datos que se utilicen. Si una fuente tiene pocos comentarios o los textos no son representativos, esto puede afectar las comparaciones.

Una similitud coseno alta no significa que los turistas estén satisfechos ni representa un porcentaje de acuerdo con la DMO.

Los temas que identifica Leiden son agrupaciones de documentos relacionados semánticamente, no categorías turísticas previamente definidas. Que dos fuentes no compartan una comunidad tampoco demuestra por sí solo que exista una brecha temática.

En el análisis de precio y valor, el percentil utilizado es una forma de seleccionar posibles comentarios de interés, no un criterio validado para clasificar opiniones económicas.

Considero que los resultados deben acompañarse de una revisión de los textos originales, especialmente cuando se analizan sentimientos, documentos atípicos y diferencias entre las fuentes.

El tiempo necesario para realizar un análisis aumenta conforme se trabaja con una mayor cantidad de documentos.

## Organización del proyecto

- `main.py`: realiza el análisis desde la terminal y conecta las distintas etapas del procesamiento.
- `app.py`: contiene la aplicación de Streamlit.
- `src/`: contiene los módulos de procesamiento, modelos, comparaciones y visualizaciones.
- `requirements.txt`: contiene las bibliotecas necesarias para ejecutar el proyecto.
- `data/pruebas/guanajuato_sintetico_100.csv`: conjunto de datos sintético para probar el funcionamiento.

No incluí los modelos descargados, los entornos virtuales, los conjuntos de datos reales ni los resultados de mis análisis en el repositorio.

Utilizo `.gitignore` para mantener estos archivos de manera local.

## Autor y contacto

**Luis Mazuca**

Universidad de Guanajuato

Campus Irapuato-Salamanca

Licenciatura en Ingeniería de Datos e Inteligencia Artificial

Correo: [mazucavazquezluisfernando@gmail.com](mailto:mazucavazquezluisfernando@gmail.com)

Si tienes alguna duda sobre el proyecto o te interesa conocer más sobre su funcionamiento, puedes contactarme por correo.
