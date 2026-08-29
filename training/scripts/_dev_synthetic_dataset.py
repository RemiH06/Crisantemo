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
    f0: float, formants: tuple[float, float, float], bandwidth: float, rng: np.random.Generator
) -> np.ndarray:
    n_samples = int(SAMPLE_RATE * DURATION_SECONDS)
    period = SAMPLE_RATE / f0
    pulse_times = []
    t = 0.0
    while t < n_samples:
        pulse_times.append(int(t))
        t += period * (1 + rng.normal(0, 0.01))  # jitter leve en el periodo
    excitation = np.zeros(n_samples)
    valid_pulses = [p for p in pulse_times if p < n_samples]
    excitation[valid_pulses] = 1.0

    signal = sum(formant_resonator(excitation, f, bandwidth, SAMPLE_RATE) for f in formants)
    signal = signal / (np.max(np.abs(signal)) + 1e-9)
    signal = signal + rng.normal(0, 0.01, size=n_samples)  # ruido leve, simula micrófono
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
                writer.writerow([str(file_path), gender, "", f"synthetic_{label}"])
                rows_written += 1

    print(f"Generadas {rows_written} voces sintéticas -> {manifest_path}")


if __name__ == "__main__":
    main()
