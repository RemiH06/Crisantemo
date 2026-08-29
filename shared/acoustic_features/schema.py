"""Generación y carga del contrato de columnas entre training y backend."""

from __future__ import annotations

import json
from pathlib import Path

from .features import FEATURE_NAMES

SCHEMA_VERSION = "v1"


def build_schema(model_version: str = "crisantemo_v1") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_version": model_version,
        "feature_names": FEATURE_NAMES,
    }


def write_schema(path: str | Path, model_version: str = "crisantemo_v1") -> None:
    Path(path).write_text(json.dumps(build_schema(model_version), indent=2, ensure_ascii=False))


def load_schema(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def assert_schema_matches(path: str | Path) -> None:
    """Falla rápido si el schema guardado no coincide con FEATURE_NAMES actual.

    Se llama al arrancar el backend: si alguien cambió features.py sin
    reentrenar y regenerar el schema, es mejor romper en el arranque que
    servir puntuaciones calculadas con columnas desalineadas.
    """
    schema = load_schema(path)
    if schema.get("feature_names") != FEATURE_NAMES:
        raise RuntimeError(
            "El feature_schema guardado no coincide con acoustic_features.FEATURE_NAMES actual. "
            "Hay que regenerar el schema y reentrenar el modelo antes de servir el backend."
        )
