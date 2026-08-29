"""Carga de audio a un array mono normalizado, compartida por training e inferencia.

Usamos librosa.load porque ya resuelve resampleo, conversión a mono y
decodificación de formatos comprimidos (via soundfile/audioread + ffmpeg
instalado en el sistema) sin que tengamos que reimplementar nada de eso.
"""

from __future__ import annotations

import numpy as np
import librosa

# Frecuencia de muestreo estándar para todo el pipeline (training e inferencia
# deben coincidir aquí; 16kHz es más que suficiente para F0 y formantes de voz
# humana, que rara vez superan los 5kHz).
TARGET_SAMPLE_RATE = 16000


def load_audio_mono(path_or_fileobj, target_sr: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Carga un archivo de audio (wav, mp3, ogg, webm, flac...) como mono float64.

    Devuelve (samples, sample_rate). Lanza cualquier excepción de librosa tal
    cual si el archivo no se puede decodificar (audio corrupto o formato no
    soportado ni por ffmpeg).
    """
    samples, sr = librosa.load(path_or_fileobj, sr=target_sr, mono=True)
    return samples.astype(np.float64), sr
