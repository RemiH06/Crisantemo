"""
Entrena el clasificador ligero sobre el vector de features (no sobre audio
crudo). Compara una regresión logística (baseline interpretable) contra
LightGBM si está disponible, y se queda con el que mejor puntúa en
validación cruzada sobre el split de train.

Los ejemplos sintéticos "adversariales" (tono y formantes en direcciones
opuestas, ver scripts/_dev_synthetic_decorrelated.py) se entrenan con más
peso que el resto: son pocos comparados con los 5,000 clips reales, y en
`docs/TRAINING_REPRODUCTION.md` sección 4.8 se documentó que aun con
formantes ya variables (no fijos), el modelo seguía sin generalizar bien la
lección a voz real. Darles más peso es el siguiente experimento barato antes
de generar más datos o cambiar features.

Uso:
    python scripts/04_train_model.py
    python scripts/04_train_model.py --adversarial-weight 1  # sin peso extra, para comparar
"""

from __future__ import annotations

import argparse

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

# Mismos nombres que ADVERSARIAL_COMBOS en 05_evaluate_model.py: los casos
# donde tono y formantes van en direcciones opuestas.
ADVERSARIAL_COMBOS = ("highf0_masculineformants", "lowf0_feminineformants")


def load_split(split_name: str) -> tuple[np.ndarray, np.ndarray, pd.Series]:
    df = pd.read_parquet(PROCESSED_DIR / f"features_{split_name}.parquet")
    X = df[FEATURE_NAMES].to_numpy()
    y = df["label"].to_numpy()
    return X, y, df["audio_path"]


def compute_sample_weights(audio_paths: pd.Series, adversarial_weight: float) -> np.ndarray:
    pattern = "|".join(ADVERSARIAL_COMBOS)
    is_adversarial = audio_paths.str.contains(pattern, regex=True)
    return np.where(is_adversarial, adversarial_weight, 1.0)


def fit_with_optional_weight(model, X, y, sample_weight):
    """Pasa sample_weight al último paso, sea un Pipeline (logreg) o el estimador directo (LightGBM)."""
    if hasattr(model, "steps"):
        step_name = model.steps[-1][0]
        model.fit(X, y, **{f"{step_name}__sample_weight": sample_weight})
    else:
        model.fit(X, y, sample_weight=sample_weight)
    return model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adversarial-weight",
        type=float,
        default=5.0,
        help="Peso relativo de los ejemplos sintéticos adversariales durante el entrenamiento final (1 = sin peso extra).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    X_train, y_train, audio_paths_train = load_split("train")
    weights = compute_sample_weights(audio_paths_train, args.adversarial_weight)
    n_adversarial = int((weights > 1.0).sum())
    print(
        f"{n_adversarial} ejemplos adversariales con peso {args.adversarial_weight}x "
        f"(de {len(weights)} filas de train)"
    )

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

    # La comparación por CV se queda sin peso extra (es solo para elegir el
    # algoritmo); el peso adversarial se aplica al entrenamiento final.
    best_name, best_model, best_score = None, None, -np.inf
    for name, model in candidates.items():
        scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
        mean_score = float(scores.mean())
        print(f"{name}: accuracy CV = {mean_score:.4f} (+/- {scores.std():.4f})")
        if mean_score > best_score:
            best_name, best_model, best_score = name, model, mean_score

    print(f"Mejor modelo: {best_name} (accuracy CV = {best_score:.4f})")
    fit_with_optional_weight(best_model, X_train, y_train, weights)

    out_path = MODELS_DIR / "crisantemo_v1_raw.joblib"
    joblib.dump(best_model, out_path)
    print(f"Modelo guardado en {out_path}")


if __name__ == "__main__":
    main()
