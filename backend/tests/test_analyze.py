from __future__ import annotations

from acoustic_features import FEATURE_NAMES


def test_analyze_returns_score_in_range(client, sine_wav_bytes):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("tone.wav", sine_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert 0 <= body["confidence"] <= 1
    assert set(body["features"].keys()) == set(FEATURE_NAMES)
    assert body["feedback"]["tone"] == "supportive"
    assert body["feedback"]["suggestions"]
    assert body["meta"]["duration_seconds"] > 0


def test_analyze_rejects_empty_file(client):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400


def test_analyze_rejects_silence(client, silence_wav_bytes):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("silence.wav", silence_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 422


def test_analyze_rejects_register_switch(client, register_switch_wav_bytes):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("switch.wav", register_switch_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 422
    assert "tono" in response.json()["detail"].lower()
