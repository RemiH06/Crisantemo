"""
Evalúa el modelo entrenado sobre el split de test: accuracy, F1, matriz de
confusión, MAE del score continuo, e importancia de features.

Dos criterios de aceptación, no solo uno:
1. La importancia de features no debe estar dominada por F0 (pitch) en
   promedio sobre todo el test set.
2. Si el test set incluye ejemplos de `_dev_synthetic_decorrelated.py`
   (tono y formantes en direcciones opuestas), el modelo debe seguir
   clasificando bien esos casos específicos. El criterio 1 es un promedio
   global y puede pasar aunque el modelo falle en casos puntuales donde tono
   y resonancia no van de la mano (ver docs/TRAINING_REPRODUCTION.md sección
   4.3/4.4, donde el criterio 1 solo no fue suficiente para detectar el
   problema).

Uso:
    python scripts/05_evaluate_model.py
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error

from acoustic_features import FEATURE_NAMES
from common import MODELS_DIR, PROCESSED_DIR, REPORTS_DIR

F0_FEATURES = {"f0_mean_hz", "f0_std_hz", "f0_range_semitones"}
F0_DOMINANCE_WARNING_THRESHOLD = 0.6

# Filas sintéticas donde tono y formantes se decorrelacionaron a propósito
# (ver scripts/_dev_synthetic_decorrelated.py y docs/TRAINING_REPRODUCTION.md
# sección 4.3/4.4). Las combinaciones "adversariales" son las que van en
# contra de la correlación natural tono-resonancia: si el modelo solo usara
# el atajo del tono, fallaría justo en estas. Es la prueba de estrés real del
# principio central del proyecto, no solo un promedio global de importancia.
DECORRELATED_MARKER = "synthetic_decorrelated"
ADVERSARIAL_COMBOS = (
    "highf0_masculineformants",
    "very_highf0_masculineformants",
    "lowf0_feminineformants",
)
ADVERSARIAL_ACCURACY_WARNING_THRESHOLD = 0.7


def _combo_tag(audio_path: str) -> str | None:
    if DECORRELATED_MARKER not in audio_path:
        return None
    # más específicos primero: "very_highf0_..." contiene "highf0_..." como substring
    for combo in (
        "lowf0_masculineformants",
        "lowf0_feminineformants",
        "very_highf0_masculineformants",
        "very_highf0_feminineformants",
        "highf0_masculineformants",
        "highf0_feminineformants",
    ):
        if combo in audio_path:
            return combo
    return None


def get_feature_importance(model) -> dict[str, float]:
    """Importancia de features del modelo, normalizada a que sume 1.

    Soporta tanto un pipeline con LogisticRegression (usa |coef_|) como un
    modelo de árboles tipo LightGBM (usa feature_importances_).
    """
    estimator = model.steps[-1][1] if hasattr(model, "steps") else model
    if hasattr(estimator, "coef_"):
        raw = np.abs(estimator.coef_[0])
    elif hasattr(estimator, "feature_importances_"):
        raw = np.asarray(estimator.feature_importances_, dtype=float)
    else:
        raise ValueError("El modelo no expone coef_ ni feature_importances_")
    total = raw.sum()
    normalized = raw / total if total > 0 else raw
    return dict(zip(FEATURE_NAMES, normalized))


def main() -> None:
    df_test = pd.read_parquet(PROCESSED_DIR / "features_test.parquet")
    X_test = df_test[FEATURE_NAMES].to_numpy()
    y_test = df_test["label"].to_numpy()

    model = joblib.load(MODELS_DIR / "crisantemo_v1_raw.joblib")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    score_continuous = y_proba * 100

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    mae = mean_absolute_error(y_test * 100, score_continuous)

    importance = get_feature_importance(model)
    f0_share = sum(v for k, v in importance.items() if k in F0_FEATURES)

    combo_tags = df_test["audio_path"].map(_combo_tag)
    adversarial_mask = combo_tags.isin(ADVERSARIAL_COMBOS)
    adversarial_accuracy = None
    if adversarial_mask.any():
        adversarial_accuracy = accuracy_score(y_test[adversarial_mask.to_numpy()], y_pred[adversarial_mask.to_numpy()])

    lines = [
        "# Reporte de evaluación: crisantemo_v1",
        "",
        f"- Accuracy: {accuracy:.4f}",
        f"- F1: {f1:.4f}",
        f"- MAE (score continuo 0-100 vs. etiqueta binaria*100): {mae:.2f}",
        f"- Matriz de confusión: {cm.tolist()}",
        "",
        "## Importancia de features",
        "",
        "| Feature | Importancia |",
        "|---|---|",
    ]
    for name, value in sorted(importance.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {value:.3f} |")

    lines += ["", f"**Peso combinado de features de F0: {f0_share:.1%}**", ""]
    if f0_share > F0_DOMINANCE_WARNING_THRESHOLD:
        lines.append(
            f"ADVERTENCIA: el modelo depende demasiado del pitch (>{F0_DOMINANCE_WARNING_THRESHOLD:.0%} "
            "de la importancia). Esto va en contra del objetivo del proyecto: revisar regularización, "
            "quitar/penalizar features de F0, o rebalancear el dataset antes de exportar."
        )
    else:
        lines.append(
            "OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras "
            "features de resonancia de forma significativa."
        )

    lines += ["", "## Prueba de estrés: tono y resonancia decorrelacionados", ""]
    if adversarial_accuracy is None:
        lines.append(
            "No hay filas de `_dev_synthetic_decorrelated.py` en este test set; esta prueba no corrió. "
            "Ver docs/TRAINING_REPRODUCTION.md sección 2C para mezclarlas."
        )
    else:
        n_adversarial = int(adversarial_mask.sum())
        lines.append(
            f"Accuracy en los {n_adversarial} casos donde tono y formantes van en direcciones opuestas "
            f"(ej. tono agudo con formantes masculinos): **{adversarial_accuracy:.1%}**."
        )
        if adversarial_accuracy < ADVERSARIAL_ACCURACY_WARNING_THRESHOLD:
            lines.append(
                f"ADVERTENCIA: por debajo de {ADVERSARIAL_ACCURACY_WARNING_THRESHOLD:.0%}. El modelo "
                "sigue usando el tono como atajo en vez de la resonancia en estos casos, que es justo lo "
                "que el proyecto busca evitar."
            )
        else:
            lines.append("OK: el modelo clasifica correctamente incluso cuando tono y resonancia no coinciden.")

    report_path = REPORTS_DIR / "eval_v1.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReporte guardado en {report_path}")


if __name__ == "__main__":
    main()
