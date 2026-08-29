"""
Descarga un subset de Mozilla Common Voice con metadata de género.

Requiere acceso a internet a huggingface.co (y opcionalmente un token en la
variable de entorno HF_TOKEN si el dataset lo pide en tu región/versión).
Este script NO se puede correr dentro del entorno donde se escribió este
proyecto (solo tiene acceso a los registros de paquetes pip/npm, no a
Hugging Face ni a otros hosts de datasets); está pensado para correrse donde
sí haya internet completo (tu máquina, un servidor, un runner de CI).

Uso:
    python scripts/01_download_dataset.py --lang es --max-rows 20000
"""

from __future__ import annotations

import argparse
import csv
import os

import soundfile as sf
from datasets import load_dataset
from tqdm import tqdm

from common import RAW_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default="es", help="Código de idioma de Common Voice (ej. es, en)")
    parser.add_argument("--split", default="validated", help="Split del dataset a usar")
    parser.add_argument("--max-rows", type=int, default=20000, help="Límite de filas a descargar")
    parser.add_argument(
        "--dataset",
        default="mozilla-foundation/common_voice_17_0",
        help="Nombre del dataset en Hugging Face",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audio_dir = RAW_DIR / args.lang
    audio_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / f"manifest_{args.lang}.csv"

    token = os.environ.get("HF_TOKEN")
    dataset = load_dataset(args.dataset, args.lang, split=args.split, token=token, streaming=True)

    rows_written = 0
    with open(manifest_path, "w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.writer(manifest_file)
        writer.writerow(["audio_path", "gender", "age", "client_id"])
        for row in tqdm(dataset, total=args.max_rows, desc=f"Descargando {args.lang}"):
            gender = (row.get("gender") or "").strip().lower()
            if not gender:
                continue  # sin metadata de género no sirve para entrenamiento supervisado
            audio = row["audio"]
            file_path = audio_dir / f"{rows_written:06d}.wav"
            sf.write(file_path, audio["array"], audio["sampling_rate"])
            writer.writerow([str(file_path), gender, row.get("age", ""), row.get("client_id", "")])
            rows_written += 1
            if rows_written >= args.max_rows:
                break

    print(f"Descargadas {rows_written} filas con género etiquetado -> {manifest_path}")


if __name__ == "__main__":
    main()
