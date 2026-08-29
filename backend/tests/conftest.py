"""Fixtures compartidas para los tests del backend.

Apunta MODEL_PATH/FEATURE_SCHEMA_PATH al modelo ya exportado en el repo
(entrenado con datos sintéticos, ver docs/TRAINING_REPRODUCTION.md) para
poder correr los tests sin Docker y sin variables de entorno propias.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

os.environ.setdefault("MODEL_PATH", str(REPO_ROOT / "models" / "crisantemo_v1.joblib"))
os.environ.setdefault(
    "FEATURE_SCHEMA_PATH", str(REPO_ROOT / "models" / "feature_schema_v1.json")
)

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

SAMPLE_RATE = 16000


def _wav_bytes(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sine_wav_bytes() -> bytes:
    duration_s = 1.5
    freq_hz = 150.0
    t = np.linspace(0, duration_s, int(SAMPLE_RATE * duration_s), endpoint=False)
    samples = 0.5 * np.sin(2 * np.pi * freq_hz * t)
    return _wav_bytes(samples)


@pytest.fixture
def silence_wav_bytes() -> bytes:
    return _wav_bytes(np.zeros(SAMPLE_RATE))
