"""Carga del modelo entrenado y validación del contrato de features al arrancar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import joblib

from acoustic_features import assert_schema_matches, load_schema


@dataclass
class ModelBundle:
    model: Any
    model_version: str
    schema_version: str


def load_model_bundle(model_path: str, feature_schema_path: str) -> ModelBundle:
    """Carga el modelo y valida que el feature schema coincida con acoustic_features.FEATURE_NAMES.

    Deja que la excepción se propague si el modelo no existe o si el schema
    está desalineado: es mejor que el backend no arranque a que sirva
    puntuaciones calculadas con columnas desalineadas.
    """
    assert_schema_matches(feature_schema_path)
    schema = load_schema(feature_schema_path)
    model = joblib.load(model_path)
    return ModelBundle(
        model=model,
        model_version=schema["model_version"],
        schema_version=schema["schema_version"],
    )
