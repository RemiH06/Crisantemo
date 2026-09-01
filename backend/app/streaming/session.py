"""Sesión de análisis en vivo: acumula el audio de un stream de WebSocket y
decide cuándo hay ventana suficiente para volver a analizar.

El cliente manda PCM crudo (Int16 mono) de forma continua; el SERVIDOR es
quien mantiene el buffer y decide la ventana, no el cliente. Así toda la
lógica de solape/suavizado vive en un solo lugar, y el navegador solo tiene
que capturar y mandar audio, no llevar su propio estado de ventaneo.
"""

from __future__ import annotations

import librosa
import numpy as np

from acoustic_features import TARGET_SAMPLE_RATE, normalize_amplitude

# Los formantes necesitan señal suficiente para estabilizarse (ver
# docs/API.md); 2.5s es un punto medio razonable entre estabilidad y
# qué tan rápido reacciona el medidor.
WINDOW_SECONDS = 2.5
# No se reanaliza en cada chunk que llega, solo cuando se acumuló esta
# cantidad de audio nuevo desde el último análisis.
STEP_SECONDS = 1.2
# Suavizado exponencial (EMA) del score mostrado, para que el medidor no
# salte de golpe entre ventanas consecutivas.
EMA_ALPHA = 0.35


class StreamingSession:
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._buffer = np.zeros(0, dtype=np.float64)
        self._samples_since_last_analysis = 0
        self._score_smoothed: float | None = None

    def add_chunk(self, pcm_int16_bytes: bytes) -> None:
        """Agrega un pedazo de audio (Int16 little-endian mono) al buffer."""
        chunk = np.frombuffer(pcm_int16_bytes, dtype=np.int16).astype(np.float64) / 32768.0
        self._buffer = np.concatenate([self._buffer, chunk])
        self._samples_since_last_analysis += len(chunk)

        max_samples = int(WINDOW_SECONDS * self.sample_rate)
        if len(self._buffer) > max_samples:
            self._buffer = self._buffer[-max_samples:]

    def ready_for_analysis(self) -> bool:
        min_samples = int(WINDOW_SECONDS * self.sample_rate)
        step_samples = int(STEP_SECONDS * self.sample_rate)
        return len(self._buffer) >= min_samples and self._samples_since_last_analysis >= step_samples

    def analysis_window(self) -> tuple[np.ndarray, int]:
        """Regresa la ventana más reciente, resampleada y normalizada igual
        que el camino de /analyze (misma función compartida, para que en
        vivo y en REST nunca diverjan)."""
        self._samples_since_last_analysis = 0
        window = self._buffer
        if self.sample_rate != TARGET_SAMPLE_RATE:
            window = librosa.resample(
                window.astype(np.float32), orig_sr=self.sample_rate, target_sr=TARGET_SAMPLE_RATE
            ).astype(np.float64)
        window = normalize_amplitude(window)
        return window, TARGET_SAMPLE_RATE

    def smooth(self, raw_score: float) -> float:
        if self._score_smoothed is None:
            self._score_smoothed = raw_score
        else:
            self._score_smoothed = EMA_ALPHA * raw_score + (1 - EMA_ALPHA) * self._score_smoothed
        return self._score_smoothed
