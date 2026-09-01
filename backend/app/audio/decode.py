"""Decodifica el audio subido a un array mono, usando el decoder compartido.

Se escribe a un archivo temporal antes de decodificar porque la ruta de
ffmpeg/audioread que usa librosa para formatos comprimidos (webm/opus del
navegador) necesita una ruta de archivo real, no puede leer un buffer en
memoria directamente. El archivo temporal se borra apenas termina de
decodificarse (bloque finally), nunca sobrevive a la respuesta ni se escribe
a ningún lugar permanente (ver docs/ETHICS_PRIVACY.md).
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
from fastapi import UploadFile

from acoustic_features import load_audio_mono

# Ninguna grabación de práctica real se acerca a esto; son topes generosos
# para no rechazar a nadie de verdad, solo evitar subidas absurdas (por
# accidente o abuso). Ver docs/API.md.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
MAX_DURATION_SECONDS = 120  # 2 minutos


class InvalidAudioError(ValueError):
    """El archivo subido está vacío, es demasiado grande/largo, o no se pudo decodificar."""


async def decode_upload(upload: UploadFile) -> tuple[np.ndarray, int]:
    raw_bytes = await upload.read()
    if not raw_bytes:
        raise InvalidAudioError("El archivo subido está vacío")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise InvalidAudioError(
            f"El archivo es muy grande ({len(raw_bytes) / 1024 / 1024:.1f}MB); "
            f"el límite es {MAX_UPLOAD_BYTES // 1024 // 1024}MB"
        )

    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(raw_bytes)
        try:
            samples, sample_rate = load_audio_mono(tmp_path)
        except Exception as exc:  # librosa/audioread lanzan distintos tipos según el backend
            raise InvalidAudioError(f"No se pudo decodificar el audio: {exc}") from exc

        duration_seconds = len(samples) / sample_rate
        if duration_seconds > MAX_DURATION_SECONDS:
            raise InvalidAudioError(
                f"La grabación dura demasiado ({duration_seconds:.0f}s); "
                f"el límite es {MAX_DURATION_SECONDS}s"
            )
        return samples, sample_rate
    finally:
        os.remove(tmp_path)
