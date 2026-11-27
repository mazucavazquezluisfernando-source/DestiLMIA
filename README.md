# DestiLMIA

**Análisis comparativo de la imagen turística proyectada por una DMO y la imagen percibida por los visitantes.**

Proyecto final de Visualización.

## Sobre el proyecto

Desarrollé DestiLMIA para comparar la imagen turística que comunican las organizaciones de promoción de destinos (DMO) con las opiniones que los visitantes comparten en plataformas de reseñas y comunidades digitales. 

El programa permite identificar los temas principales, analizar sentimientos, reconocer comentarios poco habituales y encontrar diferencias entre la comunicación oficial y las opiniones de los usuarios. También incluye un análisis de cómo se habla del precio y el valor de las experiencias turísticas.

DestiLMIA está desarrollado en Python y cuenta con una interfaz interactiva en Streamlit que facilita la exploración de los resultados mediante gráficas, tablas y comentarios representativos.

## Estructura del proyecto

Organicé los archivos de manera que cada parte del programa tenga una función clara.

| Archivo o carpeta | Descripción |
|---|---|
| `main.py` | Ejecuta y organiza el análisis. |
| `app.py` | Contiene la interfaz interactiva. |
| `src/` | Reúne los módulos de procesamiento, sentimientos, tópicos, comparaciones y visualizaciones. |
| `setup_models.py` | Prepara los modelos necesarios para analizar los textos. |
| `requirements.txt` | Contiene las bibliotecas y sus versiones. |
| `data/pruebas/` | Incluye un conjunto sintético que utilice para revisar el funcionamiento de la herramienta. |
| `Herramienta` | Aquí incluyo 5 imágenes de la herramienta con el análisis del conjunto de prueba. |
Los modelos descargados y los resultados de cada análisis se conservan localmente.

## Instalación

La instalación de esta herramienta necesita conexión a internet solo para obtener las bibliotecas y los modelos que aquelarres les digo. Una vez que están disponibles, el análisis se realiza localmente, sin utilizar APIs externas.

He probado el proyecto en **macOS con Python 3.14.7**. Incluí instrucciones de instalación para Windows y Linux con la intención de facilitar su uso en otros equipos, aunque por el momento no he podido comprobar su funcionamiento en estos sistemas, ya que no cuento con acceso a alguno de ellos.

### 1. Obtener el proyecto

Puedes copiar el repositorio mediante:

```bash
git clone https://github.com/mazucavazquezluisfernando-source/DestiLMIA.git
cd DestiLMIA
```

Si ya tienes la carpeta del proyecto, únicamente necesitas abrir una terminal dentro de ella.

### 2. Instalar las bibliotecas

Recomiendo crear un entorno virtual para mantener las bibliotecas de DestiLMIA separadas de las demás instalaciones de Python.

**macOS y Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows con PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si utilizas Windows con CMD, puedes activar el entorno mediante `.venv\Scripts\activate.bat`.

La instalación de algunas bibliotecas puede depender del sistema operativo y de la versión de Python.

### 3. Preparar los modelos

```bash
python setup_models.py
```

Este comando prepara los modelos necesarios para procesar los comentarios, comparar sus significados y analizar sentimientos.

No es necesario descargarlos nuevamente para cada análisis.

### 4. Comprobar la instalación

```bash
python --version
python -m pip check
python main.py --help
```

Estos comandos permiten consultar la versión de Python, revisar las dependencias y conocer los parámetros disponibles.

## Datos de entrada y ejecución

DestiLMIA utiliza un archivo CSV que contenga una columna de comentarios y otra que indique su fuente de origen.

El repositorio incluye 100 comentarios ficticios sobre Guanajuato para conocer el funcionamiento del programa. Este conjunto es únicamente un ejemplo: **DestiLMIA permite analizar otros destinos y fuentes**.

| resena | plataforma |
|---|---|
| Información turística de Guanajuato sobre Jardín de la Unión. Este atractivo forma parte de la oferta cultural y recreativa del destino para sus visitantes. | oficial_gto |
| Durante mi visita a Guanajuato conocí Jardín de la Unión. La visita fue agradable y el lugar estaba bien cuidado. | resenas_viajeros |
| Estoy planeando un viaje a Guanajuato y quiero conocer Jardín de la Unión. ¿Conviene visitarlo temprano para evitar las filas? | foro_turistico |

La fuente `oficial_gto` representa a la DMO. Las demás corresponden a publicaciones de usuarios.

Los nombres de las columnas y de las fuentes pueden variar según el archivo utilizado, siempre que se identifique al menos una fuente oficial y una fuente de usuarios.

### Ejecutar el análisis

El programa utiliza siete parámetros:

| Parámetro | Descripción |
|---|---|
| `--csv` | Ubicación del archivo CSV. |
| `--texto` | Columna que contiene los comentarios. |
| `--fuente` | Columna que identifica su procedencia. |
| `--dmo` | Valor que identifica a la fuente oficial. |
| `--idioma` | Idioma del análisis: español (`es`) o inglés (`en`). |
| `--titulo` | Nombre que recibirá el análisis. |
| `--paleta` | Colores de las visualizaciones. |

Puedes ejecutar el archivo de ejemplo con:

```bash
python main.py --csv data/pruebas/guanajuato_sintetico_100.csv --texto resena --fuente plataforma --dmo oficial_gto --idioma es --titulo "Imagen turística de Guanajuato" --paleta cividis
```

Las paletas disponibles son `viridis`, `cividis`, `plasma` e `inferno`.

Para consultar las opciones del programa:

```bash
python main.py --help
```

### Abrir la interfaz

Para utilizar DestiLMIA desde el navegador:

```bash
python -m streamlit run app.py
```

Desde **Nuevo análisis** puedes cargar un CSV, seleccionar sus columnas y configurar el procesamiento. En **Explorar resultados** puedes consultar los análisis que hayas realizado anteriormente.

Para detener la aplicación, presiona `Ctrl + C` en la terminal.

Cuando termines de trabajar, puedes desactivar el entorno virtual mediante:

```bash
deactivate
```

## Cómo funciona el análisis

La metodología de DestiLMIA comienza con la preparación de los comentarios. Para esta etapa se emplean **Lingua** y **spaCy**, que ayudan a identificar el idioma y procesar los textos. Después, **MiniLM** genera representaciones semánticas con las que es posible comparar comentarios que expresan ideas similares, aunque estén escritos de manera diferente. Estas representaciones sirven además para detectar documentos atípicos mediante la comparación con vecinos cercanos y el criterio estadístico **MAD**. Una vez identificados, se analizan sus palabras y expresiones frecuentes.

El análisis de sentimientos se realiza con **XLM-RoBERTa**, que permite clasificar los comentarios como positivos, negativos o neutrales. Para encontrar los temas más recurrentes se emplean **UMAP** y **Leiden**, agrupando publicaciones que comparten características semánticas. A partir de estos grupos se identifican palabras clave y comentarios representativos. El programa estudia los tópicos según su tendencia positiva o negativa y utiliza frecuencias de palabras cuando trabaja con conjuntos pequeños de documentos.

Con esta información se comparan los contenidos publicados por la **DMO** y las opiniones de los usuarios, considerando los temas identificados, la distribución de sentimientos y la cercanía semántica calculada mediante **similitud coseno**. El análisis se complementa con un apartado dedicado al **precio y valor de las experiencias turísticas**, donde se utilizan frases de referencia y similitud semántica para localizar comentarios relacionados con costos, valor percibido y relación calidad-precio.

## Visualización de resultados

Organicé la interfaz en seis secciones para facilitar la exploración de la información.

| Sección | Contenido |
|---|---|
| **Panorama** | Visión general de los documentos, fuentes y resultados principales. |
| **Opiniones** | Distribución y exploración de los sentimientos. |
| **Temas** | Grupos de comentarios relacionados y palabras principales. |
| **DMO vs usuarios** | Comparación de temas, sentimientos y alineación semántica. |
| **Precio y valor** | Comentarios relacionados con los aspectos económicos de las experiencias. |
| **Atípicos** | Publicaciones que se diferencian del contenido habitual. |

Las visualizaciones son interactivas y permiten consultar los comentarios y sus fuentes.

Los resultados nos ayudan a identificar relaciones y diferencias, pero deben interpretarse considerando el contenido original y las características de los datos. Una similitud alta no representa necesariamente satisfacción, y una diferencia temática no implica por sí sola una experiencia negativa.


## Autor y contacto

**Luis Mazuca**

Universidad de Guanajuato

Campus Irapuato-Salamanca

Licenciatura en Ingeniería de Datos e Inteligencia Artificial

**Correo:** [mazucavazquezluisfernando@gmail.com](mailto:mazucavazquezluisfernando@gmail.com)

Gracias por tu interés en DestiLMIA. Si tienes alguna pregunta sobre el funcionamiento o la metodología del proyecto, puedes comunicarte conmigo al correo indicado.

### Referencia

*XidooTopic*, versión 0.1.0. Biblioteca de Python. [PyPI](https://pypi.org/project/xidootopic/0.1.0/).
