"""Traduce el vector de features a un score 0-100 usando el modelo calibrado."""

from __future__ import annotations

from dataclasses import dataclass

from acoustic_features import AcousticFeatures

from .model_loader import ModelBundle


@dataclass
class Prediction:
    score: float
    confidence: float


def predict(bundle: ModelBundle, features: AcousticFeatures) -> Prediction:
    """Corre el modelo calibrado sobre el vector de features de una grabación.

    El modelo fue calibrado (CalibratedClassifierCV) en 06_export_model.py
    justamente para que predict_proba sea un score 0-100 confiable, no solo
    una probabilidad de clasificación binaria.
    """
    vector = features.to_vector().reshape(1, -1)
    proba_feminine = float(bundle.model.predict_proba(vector)[0, 1])
    score = proba_feminine * 100
    # Qué tan lejos está la probabilidad calibrada del punto de máxima
    # incertidumbre (0.5), normalizado a 0-1.
    confidence = abs(proba_feminine - 0.5) * 2
    return Prediction(score=score, confidence=confidence)
