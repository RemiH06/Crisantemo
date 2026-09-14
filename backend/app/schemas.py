"""Modelos de request/response de la API. Ver docs/API.md para el contrato."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from acoustic_features import FEATURE_NAMES


class FeaturesOut(BaseModel):
    f0_mean_hz: float
    f0_std_hz: float
    f0_range_semitones: float
    f1_mean_hz: float
    f2_mean_hz: float
    f3_mean_hz: float
    f2_f1_diff_hz: float
    f3_f2_diff_hz: float
    jitter_local_pct: float
    shimmer_local_pct: float
    hnr_db: float
    spectral_centroid_mean_hz: float


# Si esto falla, FeaturesOut se desalineó de acoustic_features.FEATURE_NAMES.
assert set(FeaturesOut.model_fields) == set(FEATURE_NAMES)


class MetaOut(BaseModel):
    voiced_seconds: float
    duration_seconds: float


class SuggestionOut(BaseModel):
    text: str
    # acierto (verde) = algo que ya va bien; sugerencia (azul) = tip
    # accionable; advertencia (amarillo) = algo a tener en cuenta, no del
    # habla en sí (ej. calidad de grabación); problema (rojo) = un
    # desajuste real que vale la pena trabajar. Nunca "aprobado/reprobado",
    # ver docs/ETHICS_PRIVACY.md.
    kind: Literal["acierto", "sugerencia", "advertencia", "problema"]


class FeedbackOut(BaseModel):
    summary: str
    tone: Literal["supportive"] = "supportive"
    suggestions: list[SuggestionOut]


class AnalyzeResponse(BaseModel):
    score: float = Field(ge=0, le=100)
    # Qué tan lejos está el score del punto medio (50), normalizado a 0-1.
    # 0 = el modelo está tan inseguro como pueda estar, 1 = tan seguro como pueda estar.
    # No es una medida de qué tan "correcta" es la puntuación, solo de qué tan
    # decidido está el modelo hacia un extremo u otro.
    confidence: float = Field(ge=0, le=1)
    features: FeaturesOut
    feedback: FeedbackOut
    meta: MetaOut


class ModelInfo(BaseModel):
    schema_version: str
    model_version: str
    feature_names: list[str]
