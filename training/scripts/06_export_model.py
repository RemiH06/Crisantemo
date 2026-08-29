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

from acoustic_features import FEATURE_NAMES, write_schema
from common import MODELS_DIR, PROCESSED_DIR

MODEL_VERSION = "crisantemo_v1"
REPO_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def main() -> None:
    raw_model = joblib.load(MODELS_DIR / f"{MODEL_VERSION}_raw.joblib")

    df_train = pd.read_parquet(PROCESSED_DIR / "features_train.parquet")
    X_train = df_train[FEATURE_NAMES].to_numpy()
    y_train = df_train["label"].to_numpy()

    # cv=5 sobre train re-entrena internamente y calibra con folds separados.
    # Para v1 se calibra sobre train por simplicidad; una vez que haya
    # volumen de datos real, vale la pena calibrar sobre el split de val en
    # su lugar (cv="prefit") para no reusar los mismos datos dos veces.
    calibrated_model = CalibratedClassifierCV(raw_model, method="sigmoid", cv=5)
    calibrated_model.fit(X_train, y_train)

    REPO_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = REPO_MODELS_DIR / f"{MODEL_VERSION}.joblib"
    joblib.dump(calibrated_model, model_path)
    write_schema(REPO_MODELS_DIR / "feature_schema_v1.json", model_version=MODEL_VERSION)

    print(f"Modelo calibrado exportado a {model_path}")
    print(f"Schema exportado a {REPO_MODELS_DIR / 'feature_schema_v1.json'}")


if __name__ == "__main__":
    main()
