"""
Filtra el manifest crudo a las etiquetas de género que nos sirven, balancea
clases por undersampling de la mayoritaria y separa en train/val/test
estratificado.

Uso:
    python scripts/02_prepare_labels.py --lang es
"""

from __future__ import annotations

import argparse

import pandas as pd
from sklearn.model_selection import train_test_split

from common import GENDER_LABEL_MAP, PROCESSED_DIR, RANDOM_SEED, RAW_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default="es")
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = RAW_DIR / f"manifest_{args.lang}.csv"
    df = pd.read_csv(manifest_path)

    df["gender"] = df["gender"].str.strip().str.lower()
    df = df[df["gender"].isin(GENDER_LABEL_MAP.keys())].copy()
    df["label"] = df["gender"].map(GENDER_LABEL_MAP)

    # Balancear clases: si el dataset crudo trae más de un género que del
    # otro, el modelo aprendería a favorecer la clase mayoritaria. Se
    # recorta la mayoritaria al tamaño de la minoritaria.
    counts = df["label"].value_counts()
    minority_count = int(counts.min())
    balanced_parts = [
        group.sample(n=minority_count, random_state=RANDOM_SEED) for _, group in df.groupby("label")
    ]
    df = pd.concat(balanced_parts, ignore_index=True)

    train_df, temp_df = train_test_split(
        df, test_size=args.val_size + args.test_size, stratify=df["label"], random_state=RANDOM_SEED
    )
    relative_test_size = args.test_size / (args.val_size + args.test_size)
    val_df, test_df = train_test_split(
        temp_df, test_size=relative_test_size, stratify=temp_df["label"], random_state=RANDOM_SEED
    )

    for split_name, split_df in (("train", train_df), ("val", val_df), ("test", test_df)):
        out_path = PROCESSED_DIR / f"manifest_{split_name}.csv"
        split_df.to_csv(out_path, index=False)
        print(f"{split_name}: {len(split_df)} filas -> {out_path}")


if __name__ == "__main__":
    main()
