"""Verifica en código la promesa de docs/ETHICS_PRIVACY.md: el audio nunca
sobrevive a la respuesta. `decode.py` es el único lugar del backend que
escribe a disco (necesario para que ffmpeg/audioread decodifiquen formatos
comprimidos); estos tests confirman que ese archivo temporal siempre se
borra, tanto en el camino feliz como cuando el análisis se rechaza después.
"""

from __future__ import annotations

import os


def test_no_temp_file_survives_a_successful_analyze(client, sine_wav_bytes, temp_file_spy):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("tone.wav", sine_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 200
    assert temp_file_spy, "se esperaba que decode_upload creara un archivo temporal"
    for path in temp_file_spy:
        assert not os.path.exists(path), f"el archivo temporal {path} no se borró"


def test_no_temp_file_survives_a_rejected_analyze(client, silence_wav_bytes, temp_file_spy):
    """El temporal se borra en decode_upload antes de que extract_features
    siquiera corra, así que debe limpiarse aunque el análisis se rechace
    después por voz insuficiente."""
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("silence.wav", silence_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 422
    assert temp_file_spy
    for path in temp_file_spy:
        assert not os.path.exists(path)


def test_no_temp_file_survives_invalid_audio(client, temp_file_spy):
    """Un archivo no vacío pero indecodificable también debe limpiar su temporal."""
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("garbage.wav", b"esto no es un wav valido", "audio/wav")},
    )
    assert response.status_code == 400
    assert temp_file_spy
    for path in temp_file_spy:
        assert not os.path.exists(path)
