from __future__ import annotations

import numpy as np
import pytest

from acoustic_features import TARGET_RMS, normalize_amplitude


def _rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(samples))))


def test_quiet_audio_gets_boosted_to_target_rms():
    quiet = 0.01 * np.sin(2 * np.pi * 150 * np.linspace(0, 1, 16000))
    normalized = normalize_amplitude(quiet)
    assert _rms(normalized) == pytest.approx(TARGET_RMS, rel=0.05)


def test_loud_audio_gets_reduced_to_target_rms():
    loud = 0.8 * np.sin(2 * np.pi * 150 * np.linspace(0, 1, 16000))
    normalized = normalize_amplitude(loud)
    assert _rms(normalized) == pytest.approx(TARGET_RMS, rel=0.05)


def test_normalized_audio_never_clips():
    loud = 0.99 * np.sign(np.sin(2 * np.pi * 150 * np.linspace(0, 1, 16000)))
    normalized = normalize_amplitude(loud)
    assert np.max(np.abs(normalized)) <= 1.0


def test_silence_is_left_alone_not_amplified():
    silence = np.zeros(16000)
    normalized = normalize_amplitude(silence)
    assert np.max(np.abs(normalized)) == 0.0
