"""
Genera ejemplos sintéticos donde F0 y formantes varían de forma
INDEPENDIENTE (a diferencia de _dev_synthetic_dataset.py, donde el rango de
F0 sigue estando asociado al perfil de formantes de cada clase), etiquetados
estrictamente por los formantes.

Por qué existe: con el modelo entrenado solo sobre voz real (ver
docs/TRAINING_REPRODUCTION.md sección 4.3), se encontró que el modelo
aprendió a usar el tono como atajo, porque en voces reales tono y resonancia
van correlacionados de forma natural (quien tiene voz más aguda de forma
natural también suele tener un tracto vocal más corto). Estos ejemplos
rompen esa correlación a propósito: tono agudo con formantes masculinos, y
tono grave con formantes femeninos, además de los dos casos "naturales".
Mezclados con los datos reales (ver sección 2C), fuerzan al modelo a fijarse
en los formantes para clasificar bien, no solo en el tono.

El prefijo "_dev_" marca que este script no es parte del pipeline principal
de producción (igual que _dev_synthetic_dataset.py), es un generador de
datos de apoyo para el entrenamiento, no un fixture de prueba de mecánica.

Uso:
    python scripts/_dev_synthetic_decorrelated.py --n-per-combo 200
"""

from __future__ import annotations

import argparse
import csv

import numpy as np
import soundfile as sf

from _dev_synthetic_dataset import SAMPLE_RATE, synth_vowel
from common import RAW_DIR

# Mismos perfiles de formantes que _dev_synthetic_dataset.py; la diferencia
# es que aquí el rango de F0 se elige de forma independiente del perfil de
# formantes, en vez de estar fijo por clase.
F0_RANGES = {
    "low": (85, 140),
    "high": (170, 260),
}
FORMANT_PROFILES = {
    "masculine": (730, 1090, 2440),
    "feminine": (850, 1650, 2950),
}
BANDWIDTH = 90


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-combo", type=int, default=200)
    args = parser.parse_args()

    rng = np.random.default_rng(43)  # semilla distinta a la de _dev_synthetic_dataset.py
    out_dir = RAW_DIR / "synthetic_decorrelated"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "manifest_synthetic_decorrelated.csv"

    rows_written = 0
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["audio_path", "gender", "age", "client_id"])
        for f0_name, f0_range in F0_RANGES.items():
            for formant_name, formants in FORMANT_PROFILES.items():
                gender = "female_feminine" if formant_name == "feminine" else "male_masculine"
                combo_tag = f"decorrelated_{f0_name}f0_{formant_name}formants"
                for i in range(args.n_per_combo):
                    f0 = rng.uniform(*f0_range)
                    signal = synth_vowel(f0, formants, BANDWIDTH, rng)
                    file_path = out_dir / f"{combo_tag}_{i:04d}.wav"
                    sf.write(file_path, signal, SAMPLE_RATE)
                    writer.writerow(
                        [str(file_path.relative_to(RAW_DIR)), gender, "", combo_tag]
                    )
                    rows_written += 1

    print(f"Generados {rows_written} ejemplos sintéticos decorrelacionados -> {manifest_path}")


if __name__ == "__main__":
    main()
