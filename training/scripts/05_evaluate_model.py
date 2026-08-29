"""
Evalúa el modelo entrenado sobre el split de test: accuracy, F1, matriz de
confusión, MAE del score continuo, e importancia de features.

El criterio de aceptación más importante de este reporte: la importancia no
debe estar dominada solo por las features de F0 (pitch). Si lo está, el
modelo se está saltando justo el requisito central del proyecto (que no
dependa solo del tono), y hay que revisar regularización, quitar/penalizar
features de F0, o rebalancear el dataset antes de exportar.

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

    report_path = REPORTS_DIR / "eval_v1.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReporte guardado en {report_path}")


if __name__ == "__main__":
    main()
