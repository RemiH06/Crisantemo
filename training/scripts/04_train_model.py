"""
Entrena el clasificador ligero sobre el vector de features (no sobre audio
crudo). Compara una regresión logística (baseline interpretable) contra
LightGBM si está disponible, y se queda con el que mejor puntúa en
validación cruzada sobre el split de train.

Uso:
    python scripts/04_train_model.py
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from acoustic_features import FEATURE_NAMES
from common import MODELS_DIR, PROCESSED_DIR, RANDOM_SEED

try:
    from lightgbm import LGBMClassifier

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


def load_split(split_name: str) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_parquet(PROCESSED_DIR / f"features_{split_name}.parquet")
    X = df[FEATURE_NAMES].to_numpy()
    y = df["label"].to_numpy()
    return X, y


def main() -> None:
    X_train, y_train = load_split("train")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    candidates = {
        "logreg": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
        ),
    }
    if HAS_LIGHTGBM:
        candidates["lightgbm"] = LGBMClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=RANDOM_SEED
        )

    best_name, best_model, best_score = None, None, -np.inf
    for name, model in candidates.items():
        scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
        mean_score = float(scores.mean())
        print(f"{name}: accuracy CV = {mean_score:.4f} (+/- {scores.std():.4f})")
        if mean_score > best_score:
            best_name, best_model, best_score = name, model, mean_score

    print(f"Mejor modelo: {best_name} (accuracy CV = {best_score:.4f})")
    best_model.fit(X_train, y_train)

    out_path = MODELS_DIR / "crisantemo_v1_raw.joblib"
    joblib.dump(best_model, out_path)
    print(f"Modelo guardado en {out_path}")


if __name__ == "__main__":
    main()
