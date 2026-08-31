"""Tests unitarios de extracción de features con tonos sintéticos.

Ver docs/PLAN.md, sección "Verificación": tonos sintéticos (numpy.sin a
frecuencia conocida) para validar que F0 se detecta correctamente.
"""

from __future__ import annotations

import numpy as np
import pytest

from acoustic_features import InsufficientVoiceError, UnstableVoiceError, extract_features

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


def test_register_switch_raises_unstable_voice_error():
    """Grabar grave y luego cambiar a agudo a la mitad debe rechazarse, no promediarse."""
    switched = np.concatenate([_sine_tone(110.0, duration_s=1.0), _sine_tone(300.0, duration_s=1.0)])
    with pytest.raises(UnstableVoiceError):
        extract_features(switched, SAMPLE_RATE)


def test_gradual_register_glide_raises_unstable_voice_error():
    """Deslizar el tono de grave a agudo (no un salto abrupto) también debe rechazarse.

    Una persona real probablemente desliza el tono en vez de saltar de golpe;
    un detector que solo busca un hueco en los valores no lo detectaría (se
    encontró este caso real, ver docs/API.md).
    """
    duration_s = 2.0
    n_samples = int(SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    freq_t = 110.0 * (2 ** (np.linspace(0, 12.5, n_samples) / 12))  # sube ~1 octava
    phase = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE
    glide = 0.5 * np.sin(phase)
    with pytest.raises(UnstableVoiceError):
        extract_features(glide, SAMPLE_RATE)


def test_steady_tone_does_not_raise_unstable_voice_error():
    """Un solo tono estable, aunque dure varios segundos, no debe activar la detección."""
    steady = _sine_tone(150.0, duration_s=2.0)
    features = extract_features(steady, SAMPLE_RATE)
    assert features.f0_mean_hz == pytest.approx(150.0, rel=0.02)
