"""Configuración compartida entre los scripts del pipeline de entrenamiento."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
REPORTS_DIR = DATA_DIR / "reports"

RANDOM_SEED = 42

# Mapeo de las etiquetas de género de Common Voice (varía un poco entre
# versiones del dataset) a la etiqueta binaria que usa el clasificador.
# 1 = percepción femenina, 0 = percepción masculina. Ver docs/ETHICS_PRIVACY.md
# sobre por qué esto es una limitación técnica del dataset, no una postura
# del proyecto sobre el género de nadie.
GENDER_LABEL_MAP = {
    "female_feminine": 1,
    "female": 1,
    "male_masculine": 0,
    "male": 0,
}

for _dir in (RAW_DIR, PROCESSED_DIR, MODELS_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
