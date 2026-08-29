"""Tests unitarios de extracción de features con tonos sintéticos.

Ver docs/PLAN.md, sección "Verificación": tonos sintéticos (numpy.sin a
frecuencia conocida) para validar que F0 se detecta correctamente.
"""

from __future__ import annotations

import numpy as np
import pytest

from acoustic_features import InsufficientVoiceError, extract_features

SAMPLE_RATE = 16000


def _sine_tone(freq_hz: float, duration_s: float = 1.0) -> np.ndarray:
    t = np.linspace(0, duration_s, int(SAMPLE_RATE * duration_s), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq_hz * t)


@pytest.mark.parametrize("freq_hz", [110.0, 150.0, 220.0])
def test_f0_detection_on_known_tone(freq_hz):
    features = extract_features(_sine_tone(freq_hz), SAMPLE_RATE)
    assert features.f0_mean_hz == pytest.approx(freq_hz, rel=0.02)


def test_silence_raises_insufficient_voice_error():
    silence = np.zeros(SAMPLE_RATE)
    with pytest.raises(InsufficientVoiceError):
        extract_features(silence, SAMPLE_RATE)


def test_too_short_clip_raises_insufficient_voice_error():
    short_tone = _sine_tone(150.0, duration_s=0.1)
    with pytest.raises(InsufficientVoiceError):
        extract_features(short_tone, SAMPLE_RATE)
