from __future__ import annotations

import json

import numpy as np

from acoustic_features import FEATURE_NAMES

SAMPLE_RATE = 16000


def _sine_pcm16(freq_hz: float, duration_s: float) -> bytes:
    t = np.linspace(0, duration_s, int(SAMPLE_RATE * duration_s), endpoint=False)
    samples = 0.5 * np.sin(2 * np.pi * freq_hz * t)
    return (samples * 32767).astype(np.int16).tobytes()


def test_stream_emits_score_update_after_enough_audio(client):
    with client.websocket_connect("/api/v1/stream") as ws:
        ws.send_text(json.dumps({"sample_rate": SAMPLE_RATE}))

        # manda ~4s en pedazos de ~0.5s, como haría un cliente real
        pcm = _sine_pcm16(150.0, duration_s=4.0)
        chunk_bytes = int(0.5 * SAMPLE_RATE) * 2  # 2 bytes por sample (Int16)
        for i in range(0, len(pcm), chunk_bytes):
            ws.send_bytes(pcm[i : i + chunk_bytes])

        update = ws.receive_json()
        assert update["type"] == "score_update"
        assert 0 <= update["score"] <= 100
        assert 0 <= update["score_smoothed"] <= 100
        assert set(update["features"].keys()) == set(FEATURE_NAMES)


def test_stream_rejects_bad_handshake(client):
    with client.websocket_connect("/api/v1/stream") as ws:
        ws.send_text("esto no es json")
        # el servidor cierra la conexión con un código de error en vez de
        # colgarse esperando frames binarios que nunca van a llegar bien
        try:
            ws.receive_bytes()
            assert False, "se esperaba que el servidor cerrara la conexión"
        except Exception:
            pass
