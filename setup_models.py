# Prepara los modelos necesarios para utilizar DestiLMIA.
import subprocess
import sys

from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main():
    for modelo in ("es_core_news_sm", "en_core_web_sm"):
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", modelo],
            check=True
        )

    SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    modelo = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    AutoTokenizer.from_pretrained(modelo, fix_mistral_regex=True)
    AutoModelForSequenceClassification.from_pretrained(modelo)

    print("Los modelos necesarios están disponibles.")


if __name__ == "__main__":
    main()
