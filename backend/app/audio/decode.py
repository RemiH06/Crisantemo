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


class InvalidAudioError(ValueError):
    """El archivo subido está vacío o no se pudo decodificar como audio."""


async def decode_upload(upload: UploadFile) -> tuple[np.ndarray, int]:
    raw_bytes = await upload.read()
    if not raw_bytes:
        raise InvalidAudioError("El archivo subido está vacío")

    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(raw_bytes)
        try:
            return load_audio_mono(tmp_path)
        except Exception as exc:  # librosa/audioread lanzan distintos tipos según el backend
            raise InvalidAudioError(f"No se pudo decodificar el audio: {exc}") from exc
    finally:
        os.remove(tmp_path)
