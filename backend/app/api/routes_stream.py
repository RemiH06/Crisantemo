"""WS /api/v1/stream. Ver docs/API.md para el contrato completo.

Protocolo: el cliente manda un primer mensaje de texto (JSON) con
{"sample_rate": N}, y de ahí en adelante solo frames binarios con PCM Int16
mono continuo a esa frecuencia. El servidor no espera un handshake por
chunk, solo una vez al conectar.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from acoustic_features import FEATURE_NAMES, InsufficientVoiceError, UnstableVoiceError, extract_features

from app.scoring.predictor import predict
from app.streaming.session import StreamingSession

router = APIRouter()

MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 192000


@router.websocket("/api/v1/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        handshake_raw = await websocket.receive_text()
        handshake = json.loads(handshake_raw)
        sample_rate = int(handshake["sample_rate"])
        if not (MIN_SAMPLE_RATE <= sample_rate <= MAX_SAMPLE_RATE):
            raise ValueError(f"sample_rate fuera de rango: {sample_rate}")
    except WebSocketDisconnect:
        return
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        await websocket.close(code=1002, reason=f"handshake inválido: {exc}")
        return

    session = StreamingSession(sample_rate=sample_rate)
    bundle = websocket.app.state.model_bundle

    try:
        while True:
            chunk = await websocket.receive_bytes()
            session.add_chunk(chunk)

            if not session.ready_for_analysis():
                continue

            samples, sr = session.analysis_window()
            try:
                features = extract_features(samples, sr)
            except (InsufficientVoiceError, UnstableVoiceError):
                # Silencio, o la ventana cayó justo en medio de una
                # transición de tono: no hay nada confiable que reportar
                # todavía, se espera a la siguiente ventana.
                continue

            prediction = predict(bundle, features)
            score_smoothed = session.smooth(prediction.score)
            feature_values = features.as_dict()
            feature_values.pop("voiced_seconds")
            feature_values.pop("duration_seconds")

            await websocket.send_json(
                {
                    "type": "score_update",
                    "score": prediction.score,
                    "score_smoothed": score_smoothed,
                    "features": {name: feature_values[name] for name in FEATURE_NAMES},
                }
            )
    except WebSocketDisconnect:
        pass
