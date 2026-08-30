"""
Calibra el modelo entrenado (para que predict_proba sea un score 0-100
confiable, no solo una clasificación binaria) y lo exporta junto con el
feature schema a models/ en la raíz del repo, el volumen que monta el
backend en producción.

Uso:
    python scripts/06_export_model.py
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from acoustic_features import FEATURE_NAMES, write_schema
from common import MODELS_DIR, PROCESSED_DIR

MODEL_VERSION = "crisantemo_v1"
REPO_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def main() -> None:
    raw_model = joblib.load(MODELS_DIR / f"{MODEL_VERSION}_raw.joblib")

    # cv="prefit" + split de validación en vez de cv=5 sobre train: probamos
    # cv=5 primero y encontró dos problemas reales (ver
    # docs/TRAINING_REPRODUCTION.md sección 4.9). 1) CalibratedClassifierCV
    # con cv=5 CLONA y REENTRENA raw_model desde cero en cada fold, así que
    # si 04_train_model.py se corrió con --adversarial-weight, ese peso se
    # pierde aquí a menos que se lo pasemos otra vez explícitamente (el
    # modelo exportado daba resultados idénticos a sin peso, porque este
    # paso lo estaba descartando en silencio). 2) Aun pasándolo, reentrenar
    # 5 copias con menos datos cada una diluye el efecto del peso: el modelo
    # crudo (ya entrenado una sola vez, con todo el peso) se comportaba
    # mucho mejor que cualquiera de las 5 copias recalibradas. cv="prefit"
    # usa raw_model tal cual (con su peso ya adentro) y solo ajusta la curva
    # de calibración sobre datos que no vio en entrenamiento (val), sin
    # volver a tocar los pesos. FrozenEstimator (sklearn >= 1.6) es el
    # reemplazo de cv="prefit" (removido): envuelve un modelo ya entrenado
    # para que CalibratedClassifierCV lo use tal cual, sin reentrenarlo.
    df_val = pd.read_parquet(PROCESSED_DIR / "features_val.parquet")
    X_val = df_val[FEATURE_NAMES].to_numpy()
    y_val = df_val["label"].to_numpy()

    calibrated_model = CalibratedClassifierCV(FrozenEstimator(raw_model), method="sigmoid")
    calibrated_model.fit(X_val, y_val)

    REPO_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = REPO_MODELS_DIR / f"{MODEL_VERSION}.joblib"
    joblib.dump(calibrated_model, model_path)
    write_schema(REPO_MODELS_DIR / "feature_schema_v1.json", model_version=MODEL_VERSION)

    print(f"Modelo calibrado exportado a {model_path}")
    print(f"Schema exportado a {REPO_MODELS_DIR / 'feature_schema_v1.json'}")


if __name__ == "__main__":
    main()
