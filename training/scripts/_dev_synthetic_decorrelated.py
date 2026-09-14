"""
Genera ejemplos sintéticos donde F0 y formantes varían de forma
INDEPENDIENTE (a diferencia de _dev_synthetic_dataset.py, donde el rango de
F0 sigue estando asociado al perfil de formantes de cada clase), etiquetados
estrictamente por los formantes.

Por qué existe: con el modelo entrenado solo sobre voz real (ver
docs/TRAINING_REPRODUCTION.md sección 4.3), se encontró que el modelo
aprendió a usar el tono como atajo. `training/notebooks/feature_analysis.ipynb`
encontró la razón exacta: F0 solo tiene AUC 0.97 clasificando género en
Common Voice (casi perfecto), los formantes solos apenas 0.57-0.73 (la
correlación entre ambos es en realidad débil, r=0.10-0.37). No es que el
modelo "prefiera" el atajo, es la señal objetivamente más fuerte que tiene.
Además, tonos agudos actuados reales (320-356 Hz) caen fuera de todo el
rango de F0 que el dataset real cubre (que no pasa de ~300 Hz), así que ahí
el modelo extrapola sin ningún ejemplo de referencia.

Estos ejemplos rompen la asociación tono-formantes a propósito, y el rango
"very_high" cubre justo la zona de tono agudo actuado real donde se
encontró el problema (antes solo llegábamos a 260 Hz). Mezclados con los
datos reales (ver sección 2C) y en cantidad suficiente para no diluirse
(la primera vez, 800 contra 5,000 reales no alcanzó, ver sección 4.4),
fuerzan al modelo a fijarse en los formantes para clasificar bien en esa
zona, no solo en el tono.

El prefijo "_dev_" marca que este script no es parte del pipeline principal
de producción (igual que _dev_synthetic_dataset.py), es un generador de
datos de apoyo para el entrenamiento, no un fixture de prueba de mecánica.

Uso:
    python scripts/_dev_synthetic_decorrelated.py --n-per-combo 500
"""

from __future__ import annotations

import argparse
import csv

import numpy as np
import soundfile as sf

from _dev_synthetic_dataset import SAMPLE_RATE, synth_vowel
from common import RAW_DIR

# El rango de F0 se elige de forma independiente del perfil de formantes, en
# vez de estar fijo por clase. "very_high" se agregó después de encontrar
# que voz aguda actuada real llega hasta ~356 Hz, fuera del rango que
# cualquier otra parte del pipeline había cubierto hasta ahora.
F0_RANGES = {
    "low": (85, 140),
    "high": (170, 260),
    "very_high": (280, 400),
}

# Confirmado con grabaciones reales nuevas (ver docs/TRAINING_REPRODUCTION.md
# sección 4.14): forzar el tono muy por fuera del registro cómodo no solo
# sube F0, también limpia la fonación de verdad (jitter/shimmer bajísimos,
# HNR altísimo comparado con voz normal de la misma persona, mismo
# micrófono). No es ruido de grabación, es una firma fisiológica real de
# tono forzado. Antes, el rango very_high se sintetizaba con el mismo
# jitter/shimmer/ruido "normal" que low/high, así que el modelo nunca vio
# esa combinación específica (F0 extremo + fonación anormalmente limpia)
# etiquetada como masculina. Estos rangos, calibrados empíricamente contra
# esa grabación real, son deliberadamente un rango angosto (no un valor
# fijo, para no repetir el error de "huella digital sintética" de la
# sección 4.7) muy por debajo de los defaults de synth_vowel().
VERY_HIGH_F0_NOISE_RANGES = {
    "jitter_std": (0.001, 0.004),
    "shimmer_std": (0.003, 0.010),
    "noise_std": (0.0001, 0.0006),
}

# Media y desviación estándar de F1/F2/F3 por género, calculadas sobre los
# datos reales de entrenamiento (ver training/notebooks/feature_analysis.ipynb).
# Antes se usaban dos formantes FIJOS exactos (730/1090/2440 y 850/1650/2950,
# ni siquiera dentro del rango real: el F1 real masculino promedia 456Hz, no
# 730). Con solo 2 valores exactos repetidos miles de veces, un modelo de
# árboles puede aprender a reconocer esos números precisos como "esto es
# sintético" en vez de aprender el patrón de resonancia real (ver
# docs/TRAINING_REPRODUCTION.md sección 4.7). Muestrear de una distribución
# continua calibrada a los datos reales cierra ese atajo y además hace que
# los ejemplos sintéticos caigan dentro del rango de formantes real.
FORMANT_STATS = {
    "masculine": {"f1": (455.7, 58.7), "f2": (1582.4, 142.5), "f3": (2628.9, 156.1)},
    "feminine": {"f1": (488.4, 51.6), "f2": (1681.2, 183.6), "f3": (2764.9, 171.8)},
}
BANDWIDTH = 90


def _sample_formants(profile_name: str, rng: np.random.Generator) -> tuple[float, float, float]:
    stats = FORMANT_STATS[profile_name]
    f1 = float(rng.normal(*stats["f1"]))
    f2 = float(rng.normal(*stats["f2"]))
    f3 = float(rng.normal(*stats["f3"]))
    # Mantener el orden físico F1 < F2 < F3 con margen mínimo, por si una
    # muestra rara de la normal saliera fuera de orden.
    f2 = max(f2, f1 + 200)
    f3 = max(f3, f2 + 200)
    return f1, f2, f3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-combo", type=int, default=500)
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
            for formant_name in FORMANT_STATS:
                gender = "female_feminine" if formant_name == "feminine" else "male_masculine"
                combo_tag = f"decorrelated_{f0_name}f0_{formant_name}formants"
                for i in range(args.n_per_combo):
                    f0 = rng.uniform(*f0_range)
                    formants = _sample_formants(formant_name, rng)
                    if f0_name == "very_high":
                        noise_kwargs = {
                            name: rng.uniform(*bounds) for name, bounds in VERY_HIGH_F0_NOISE_RANGES.items()
                        }
                    else:
                        noise_kwargs = {}
                    signal = synth_vowel(f0, formants, BANDWIDTH, rng, **noise_kwargs)
                    file_path = out_dir / f"{combo_tag}_{i:04d}.wav"
                    sf.write(file_path, signal, SAMPLE_RATE)
                    writer.writerow(
                        [str(file_path.relative_to(RAW_DIR)), gender, "", combo_tag]
                    )
                    rows_written += 1

    print(f"Generados {rows_written} ejemplos sintéticos decorrelacionados -> {manifest_path}")


if __name__ == "__main__":
    main()
