"""
Generador de un dataset sintético pequeño, SOLO para validar la mecánica del
pipeline de entrenamiento en un entorno sin acceso a Common Voice. NO debe
usarse para producir el modelo real: las voces son sintetizadas con un
sintetizador de formantes simplificado (pulsos glotales filtrados por
resonadores), no son grabaciones de personas reales.

Genera dos clases separables tanto por pitch como por resonancia (formantes),
para poder verificar que los scripts 02-06 funcionan de punta a punta y que
el pipeline efectivamente puede aprender a usar formantes, no solo F0.

El prefijo "_dev_" (en vez de un número) marca que este script no forma
parte del pipeline real de producción.

Uso:
    python scripts/_dev_synthetic_dataset.py --n-per-class 150
"""

from __future__ import annotations

import argparse
import csv

import numpy as np
import soundfile as sf
from scipy.signal import lfilter

from common import RANDOM_SEED, RAW_DIR

SAMPLE_RATE = 16000
DURATION_SECONDS = 1.5

# Rangos de F0 y formantes usados para sintetizar dos clases separables.
# Estos valores están inspirados en rangos típicos reportados en fonética
# para una vocal /a/ en voces adultas graves vs. agudas con más resonancia,
# pero aquí son solo parámetros de síntesis, no una medida clínica de nada.
VOICE_PROFILES = {
    0: {"f0_range": (85, 140), "formants": (730, 1090, 2440), "bandwidth": 90},  # clase "grave"
    1: {"f0_range": (170, 260), "formants": (850, 1650, 2950), "bandwidth": 90},  # clase "aguda+resonante"
}


def formant_resonator(signal: np.ndarray, freq: float, bandwidth: float, sr: int) -> np.ndarray:
    r = np.exp(-np.pi * bandwidth / sr)
    theta = 2 * np.pi * freq / sr
    a1 = 2 * r * np.cos(theta)
    a2 = -r * r
    return lfilter([1.0], [1.0, -a1, -a2], signal)


def synth_vowel(
    f0: float,
    formants: tuple[float, float, float],
    bandwidth: float,
    rng: np.random.Generator,
    jitter_std: float | None = None,
    shimmer_std: float | None = None,
    noise_std: float | None = None,
    intonation_semitone_std: float | None = None,
) -> np.ndarray:
    """Sintetiza una vocal con pulsos glotales filtrados por resonadores de formantes.

    jitter_std/shimmer_std/noise_std controlan qué tan "áspera" suena la voz
    (variación periodo a periodo, variación de amplitud pulso a pulso, y
    ruido de fondo). intonation_semitone_std controla cuánto sube y baja el
    tono a lo largo de la grabación (entonación natural de una oración), en
    vez de un tono sostenido parejo. Si se dejan en None, cada llamada saca
    su propia severidad al azar dentro de un rango calibrado para que
    jitter_local_pct/shimmer_local_pct/hnr_db/f0_std_hz/f0_range_semitones
    terminen en rangos parecidos a voz real, no sospechosamente más limpios
    (ver docs/TRAINING_REPRODUCTION.md sección 4.6: un modelo entrenado con
    voces sintéticas demasiado limpias/parejas puede aprender a distinguir
    "sintético vs. real" por esas features en vez de aprender la lección de
    tono/resonancia que se buscaba enseñarle; un tono sostenido sin
    entonación resultó ser la señal más delatora de todas).
    """
    n_samples = int(SAMPLE_RATE * DURATION_SECONDS)
    if jitter_std is None:
        jitter_std = rng.uniform(0.010, 0.035)
    if shimmer_std is None:
        shimmer_std = rng.uniform(0.03, 0.11)
    if noise_std is None:
        noise_std = rng.uniform(0.0025, 0.013)
    if intonation_semitone_std is None:
        intonation_semitone_std = rng.uniform(2.0, 5.0)

    # Contorno de entonación: unos pocos puntos de control al azar,
    # interpolados suavemente a lo largo de la grabación, para que el tono
    # suba y baje como en una oración real en vez de quedarse fijo.
    n_control_points = 8
    control_semitones = rng.normal(0, intonation_semitone_std, n_control_points)
    control_semitones -= control_semitones.mean()
    contour_semitones = np.interp(
        np.arange(n_samples),
        np.linspace(0, n_samples - 1, n_control_points),
        control_semitones,
    )

    pulse_times = []
    pulse_gains = []
    t = 0.0
    while t < n_samples:
        instantaneous_f0 = f0 * (2.0 ** (contour_semitones[min(int(t), n_samples - 1)] / 12.0))
        period = SAMPLE_RATE / instantaneous_f0
        pulse_times.append(int(t))
        pulse_gains.append(max(0.05, 1.0 + rng.normal(0, shimmer_std)))
        t += period * (1 + rng.normal(0, jitter_std))
    excitation = np.zeros(n_samples)
    for pulse_t, gain in zip(pulse_times, pulse_gains):
        if pulse_t < n_samples:
            excitation[pulse_t] = gain

    signal = sum(formant_resonator(excitation, f, bandwidth, SAMPLE_RATE) for f in formants)
    signal = signal / (np.max(np.abs(signal)) + 1e-9)
    signal = signal + rng.normal(0, noise_std, size=n_samples)
    return signal.astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-class", type=int, default=150)
    args = parser.parse_args()

    rng = np.random.default_rng(RANDOM_SEED)
    out_dir = RAW_DIR / "synthetic_dev"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "manifest_synthetic_dev.csv"

    rows_written = 0
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["audio_path", "gender", "age", "client_id"])
        for label, profile in VOICE_PROFILES.items():
            gender = "female_feminine" if label == 1 else "male_masculine"
            for i in range(args.n_per_class):
                f0 = rng.uniform(*profile["f0_range"])
                signal = synth_vowel(f0, profile["formants"], profile["bandwidth"], rng)
                file_path = out_dir / f"{gender}_{i:04d}.wav"
                sf.write(file_path, signal, SAMPLE_RATE)
                writer.writerow([str(file_path.relative_to(RAW_DIR)), gender, "", f"synthetic_{label}"])
                rows_written += 1

    print(f"Generadas {rows_written} voces sintéticas -> {manifest_path}")


if __name__ == "__main__":
    main()
