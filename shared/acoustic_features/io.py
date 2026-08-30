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

# Nivel de referencia (RMS) al que se normaliza todo audio de entrada, para
# que diferencias de volumen de grabación (micrófono, distancia, ganancia del
# navegador) no se cuelen como ruido en features sensibles a la amplitud
# (HNR, shimmer, brillo espectral). 0.1 es un nivel de voz cómodo sin
# arriesgar clipping en la mayoría de las grabaciones.
TARGET_RMS = 0.1

# Por debajo de este RMS se considera silencio/ruido de piso: no tiene caso
# amplificarlo (subiría el ruido de fondo, no la señal de voz), y evita una
# división por un número casi cero.
_SILENCE_RMS_FLOOR = 1e-6


def normalize_amplitude(samples: np.ndarray, target_rms: float = TARGET_RMS) -> np.ndarray:
    """Escala el audio a un RMS (volumen percibido) de referencia.

    A diferencia de normalizar solo por el pico (evitar clipping), normalizar
    por RMS iguala qué tan "fuerte" suena la grabación en promedio, que es lo
    que de verdad varía entre micrófonos/distancias/ganancia y lo que puede
    ensuciar features como HNR o shimmer si no se controla.
    """
    rms = float(np.sqrt(np.mean(np.square(samples))))
    if rms < _SILENCE_RMS_FLOOR:
        return samples
    normalized = samples * (target_rms / rms)
    peak = float(np.max(np.abs(normalized)))
    if peak > 1.0:
        normalized = normalized / peak
    return normalized


def load_audio_mono(path_or_fileobj, target_sr: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Carga un archivo de audio (wav, mp3, ogg, webm, flac...) como mono float64,
    resampleado a target_sr y normalizado en amplitud (ver normalize_amplitude).

    Devuelve (samples, sample_rate). Lanza cualquier excepción de librosa tal
    cual si el archivo no se puede decodificar (audio corrupto o formato no
    soportado ni por ffmpeg).
    """
    samples, sr = librosa.load(path_or_fileobj, sr=target_sr, mono=True)
    samples = normalize_amplitude(samples.astype(np.float64))
    return samples, sr
