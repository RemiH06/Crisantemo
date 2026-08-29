"""
Extrae el vector de features acústicas para cada fila de los manifests de
train/val/test, usando acoustic_features (el mismo módulo que usa el
backend en producción, para que nunca haya divergencia entre entrenamiento
e inferencia).

Uso:
    python scripts/03_extract_features.py
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
from tqdm import tqdm

from acoustic_features import FEATURE_NAMES, extract_features, load_audio_mono
from common import PROCESSED_DIR, RAW_DIR


def extract_for_split(split_name: str) -> None:
    manifest_path = PROCESSED_DIR / f"manifest_{split_name}.csv"
    manifest = pd.read_csv(manifest_path)

    rows = []
    skip_reasons: Counter[str] = Counter()
    for _, row in tqdm(manifest.iterrows(), total=len(manifest), desc=f"Features {split_name}"):
        try:
            samples, sr = load_audio_mono(RAW_DIR / row["audio_path"])
            feats = extract_features(samples, sr)
        except Exception as exc:  # audio corrupto, formato no soportado, o sin voz suficiente
            skip_reasons[type(exc).__name__] += 1
            continue
        record = {name: getattr(feats, name) for name in FEATURE_NAMES}
        record["label"] = row["label"]
        record["audio_path"] = row["audio_path"]
        rows.append(record)

    out_path = PROCESSED_DIR / f"features_{split_name}.parquet"
    pd.DataFrame(rows).to_parquet(out_path, index=False)
    total_skipped = sum(skip_reasons.values())
    print(f"{split_name}: {len(rows)} filas procesadas, {total_skipped} descartadas -> {out_path}")
    if skip_reasons:
        print(f"  motivos de descarte: {dict(skip_reasons)}")


def main() -> None:
    for split_name in ("train", "val", "test"):
        extract_for_split(split_name)


if __name__ == "__main__":
    main()
