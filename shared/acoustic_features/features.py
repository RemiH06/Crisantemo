"""Extracción del vector de features acústicas.

Este módulo es el contrato compartido entre `training/` (que lo usa para
construir el dataset de entrenamiento) y `backend/` (que lo usa para puntuar
audio en producción). Nunca debe haber dos implementaciones distintas de esto:
si algo cambia aquí, hay que reentrenar el modelo.

El requisito de producto detrás de este diseño: la puntuación no puede
depender solo del pitch (F0). Por eso el vector incluye formantes (F1-F3,
que reflejan la resonancia del tracto vocal) y medidas de calidad de voz
(jitter, shimmer, HNR), no solo estadísticas de F0.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import parselmouth
from parselmouth.praat import call
import librosa

F0_FLOOR_HZ = 75.0
F0_CEILING_HZ = 500.0

# Duración mínima de voz sonora (no silencio) requerida para poder confiar en
# el análisis de formantes/jitter/shimmer, que necesitan varios ciclos de
# vibración glotal para estabilizarse.
MIN_VOICED_SECONDS = 0.3

# Orden y nombres exactos del vector de features. Este orden es el que se
# serializa en models/feature_schema_v1.json y el que el modelo espera en
# predict(). No reordenar sin regenerar el schema y reentrenar.
FEATURE_NAMES: list[str] = [
    "f0_mean_hz",
    "f0_std_hz",
    "f0_range_semitones",
    "f1_mean_hz",
    "f2_mean_hz",
    "f3_mean_hz",
    "f2_f1_diff_hz",
    "f3_f2_diff_hz",
    "jitter_local_pct",
    "shimmer_local_pct",
    "hnr_db",
    "spectral_centroid_mean_hz",
]


class InsufficientVoiceError(ValueError):
    """El audio no contiene suficiente señal de voz sonora para analizarlo."""


@dataclass
class AcousticFeatures:
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
    # Metadata que acompaña la respuesta pero NO forma parte del vector que
    # ve el modelo (no es una propiedad de la voz, es una medida de calidad
    # de la señal analizada).
    voiced_seconds: float
    duration_seconds: float

    def as_dict(self) -> dict:
        return asdict(self)

    def to_vector(self) -> np.ndarray:
        """Vector ordenado según FEATURE_NAMES, listo para el modelo."""
        values = asdict(self)
        return np.array([values[name] for name in FEATURE_NAMES], dtype=np.float64)


def _safe_mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def extract_features(samples: np.ndarray, sample_rate: int) -> AcousticFeatures:
    """Extrae el vector de features acústicas de una señal de audio mono.

    samples: array 1D float64/float32 normalizado en [-1, 1].
    sample_rate: frecuencia de muestreo en Hz (debe coincidir con la usada
        al cargar el audio, ver acoustic_features.io.load_audio_mono).

    Lanza InsufficientVoiceError si no hay suficiente señal sonora (silencio,
    ruido, o clip demasiado corto) para confiar en el análisis.
    """
    if samples.ndim != 1:
        raise ValueError("Se espera audio mono (array 1D)")

    duration_seconds = len(samples) / sample_rate
    sound = parselmouth.Sound(samples.astype(np.float64), sampling_frequency=sample_rate)

    pitch = sound.to_pitch(pitch_floor=F0_FLOOR_HZ, pitch_ceiling=F0_CEILING_HZ)
    f0_track = pitch.selected_array["frequency"]
    voiced_f0 = f0_track[f0_track > 0]
    voiced_seconds = float(len(voiced_f0) * pitch.time_step)

    if voiced_seconds < MIN_VOICED_SECONDS:
        raise InsufficientVoiceError(
            f"Solo se detectaron {voiced_seconds:.2f}s de voz sonora; "
            f"se requieren al menos {MIN_VOICED_SECONDS}s para un análisis confiable"
        )

    f0_mean = float(np.mean(voiced_f0))
    f0_std = float(np.std(voiced_f0))
    f0_min, f0_max = float(np.min(voiced_f0)), float(np.max(voiced_f0))
    f0_range_semitones = 12.0 * np.log2(f0_max / f0_min) if f0_min > 0 else 0.0

    formant = sound.to_formant_burg(max_number_of_formants=5)
    f1_values, f2_values, f3_values = [], [], []
    for t, f0_at_t in zip(pitch.ts(), f0_track):
        if f0_at_t <= 0:
            continue
        for formant_number, bucket in ((1, f1_values), (2, f2_values), (3, f3_values)):
            value = formant.get_value_at_time(formant_number, t)
            if value is not None and not np.isnan(value):
                bucket.append(value)

    f1_mean = _safe_mean(f1_values)
    f2_mean = _safe_mean(f2_values)
    f3_mean = _safe_mean(f3_values)

    point_process = call(sound, "To PointProcess (periodic, cc)", F0_FLOOR_HZ, F0_CEILING_HZ)
    jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    shimmer_local = call(
        [sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
    )
    jitter_local_pct = float(jitter_local) * 100 if jitter_local == jitter_local else 0.0
    shimmer_local_pct = float(shimmer_local) * 100 if shimmer_local == shimmer_local else 0.0

    harmonicity = sound.to_harmonicity_cc(minimum_pitch=F0_FLOOR_HZ)
    hnr_values = harmonicity.values[harmonicity.values != -200]
    hnr_db = float(np.mean(hnr_values)) if hnr_values.size else 0.0

    spectral_centroid = librosa.feature.spectral_centroid(
        y=samples.astype(np.float32), sr=sample_rate
    )
    spectral_centroid_mean_hz = float(np.mean(spectral_centroid))

    return AcousticFeatures(
        f0_mean_hz=f0_mean,
        f0_std_hz=f0_std,
        f0_range_semitones=float(f0_range_semitones),
        f1_mean_hz=f1_mean,
        f2_mean_hz=f2_mean,
        f3_mean_hz=f3_mean,
        f2_f1_diff_hz=f2_mean - f1_mean,
        f3_f2_diff_hz=f3_mean - f2_mean,
        jitter_local_pct=jitter_local_pct,
        shimmer_local_pct=shimmer_local_pct,
        hnr_db=hnr_db,
        spectral_centroid_mean_hz=spectral_centroid_mean_hz,
        voiced_seconds=voiced_seconds,
        duration_seconds=float(duration_seconds),
    )
