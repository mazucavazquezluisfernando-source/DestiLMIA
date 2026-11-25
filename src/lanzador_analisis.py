import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
TRABAJOS = RAIZ / "resultados" / "trabajos_web"
ENTRADAS = RAIZ / "data" / "entradas_web"


def guardar_estado(carpeta, estado, **datos):

    contenido = {"estado": estado, **datos}

    temporal = carpeta / "estado.tmp"
    temporal.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )
    temporal.replace(carpeta / "estado.json")


def iniciar_analisis(
    contenido, texto, fuente, dmo,
    idioma, titulo, paleta, procedencia
):

    if not contenido or len(contenido) > 30 * 1024 * 1024:
        raise ValueError("El CSV debe tener como máximo 30 MB.")

    if idioma not in {"es", "en"}:
        raise ValueError("Idioma no permitido.")

    if paleta not in {"viridis", "cividis", "plasma", "inferno"}:
        raise ValueError("Paleta no permitida.")

    identificador = uuid.uuid4().hex[:12]

    carpeta = TRABAJOS / identificador
    carpeta.mkdir(parents=True)

    ENTRADAS.mkdir(parents=True, exist_ok=True)

    ruta_csv = ENTRADAS / f"{identificador}.csv"
    ruta_csv.write_bytes(contenido)

    configuracion = {
        "csv": str(ruta_csv.relative_to(RAIZ)),
        "texto": texto,
        "fuente": fuente,
        "dmo": dmo,
        "idioma": idioma,
        "titulo": titulo,
        "paleta": paleta,
        "procedencia": procedencia,
    }

    (carpeta / "configuracion.json").write_text(
        json.dumps(
            configuracion,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    guardar_estado(carpeta, "iniciado", titulo=titulo)

    comando = [
        sys.executable,
        "-u",
        str(Path(__file__).resolve()),
        "--worker",
        str(carpeta),
    ]

    try:
        with (carpeta / "lanzador.log").open("w") as salida:
            subprocess.Popen(
                comando,
                cwd=RAIZ,
                stdout=salida,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
    except OSError as error:
        guardar_estado(carpeta, "error", mensaje=str(error))
        raise

    return identificador


def consultar_estado(identificador):

    ruta = TRABAJOS / identificador / "estado.json"

    if not ruta.is_file():
        return {"estado": "no_encontrado"}

    return json.loads(ruta.read_text(encoding="utf-8"))


def ejecutar_trabajador(carpeta):

    configuracion = json.loads(
        (carpeta / "configuracion.json").read_text(
            encoding="utf-8"
        )
    )

    base = RAIZ / "resultados" / "cli"
    anteriores = set(base.glob("ejecucion_*")) if base.exists() else set()

    comando = [sys.executable, "-u", str(RAIZ / "main.py")]

    for parametro in [
        "csv", "texto", "fuente", "dmo",
        "idioma", "titulo", "paleta"
    ]:
        comando.extend([
            "--" + parametro,
            configuracion[parametro]
        ])

    entorno = os.environ.copy()
    entorno.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "DESTILMIA_PROCEDENCIA": configuracion["procedencia"],
    })

    guardar_estado(
        carpeta,
        "procesando",
        titulo=configuracion["titulo"]
    )

    try:
        with (carpeta / "procesamiento.log").open("w") as salida:
            resultado = subprocess.run(
                comando,
                cwd=RAIZ,
                env=entorno,
                stdout=salida,
                stderr=subprocess.STDOUT,
                check=False
            )

        if resultado.returncode != 0:
            guardar_estado(
                carpeta,
                "error",
                mensaje="El motor terminó con un error."
            )
            return

        nuevas = sorted(
            set(base.glob("ejecucion_*")) - anteriores
        )

        candidatas = []

        for nueva in nuevas:
            ruta_meta = nueva / "metadatos_analisis.json"

            if not ruta_meta.is_file():
                continue

            meta = json.loads(
                ruta_meta.read_text(encoding="utf-8")
            )

            if (
                meta.get("archivo_entrada")
                == configuracion["csv"]
                and meta.get("estado") == "finalizado"
            ):
                candidatas.append(nueva)

        if len(candidatas) != 1:
            raise RuntimeError(
                "No se pudo identificar un único análisis terminado."
            )

        nueva = candidatas[0]

        guardar_estado(
            carpeta,
            "finalizado",
            titulo=configuracion["titulo"],
            carpeta_resultados=str(nueva.relative_to(RAIZ))
        )

    except Exception as error:
        guardar_estado(
            carpeta,
            "error",
            mensaje=str(error)
        )


if __name__ == "__main__" and len(sys.argv) == 3:
    if sys.argv[1] == "--worker":
        ejecutar_trabajador(Path(sys.argv[2]))
