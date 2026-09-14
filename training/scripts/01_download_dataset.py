"""
Descarga un corpus con etiqueta de género desde Mozilla Data Collective (MDC).

Common Voice se movió de Hugging Face a Mozilla Data Collective en octubre de
2025; el mirror en Hugging Face quedó vacío a propósito (ver
docs/TRAINING_REPRODUCTION.md). Requiere una cuenta en mozilladatacollective.com
con los términos de cada dataset aceptados desde su sitio web (la API no deja
aceptarlos), y un API key en la variable de entorno MDC_API_KEY.

Por defecto usa dos datasets curados oficialmente por "MDC Curators": Common
Voice Scripted Speech 26.0, español mexicano, ya filtrados por género
autorreportado y solo audio validado (al menos un upvote, cero downvotes).
Cada uno es un .tar.gz con clips/*.mp3. Se transmite y descomprime el .tar.gz
al vuelo, tomando los primeros --max-rows/2 clips de cada género sin bajar el
archivo completo a disco (los datasets completos pesan ~1.8GB y ~2GB; para
una corrida de validación no hace falta bajarlos enteros).

También soporta otros idiomas ya curados por género en MDC (ver
LANGUAGE_DATASETS abajo: en-US, nl-NL, árabe por ahora), para comparar cómo
se comportan las features acústicas por idioma/región, no solo por género
(ver training/notebooks/feature_analysis.ipynb sección 6). Cada idioma nuevo
necesita su propia aceptación de términos en el sitio web antes de que la API
deje descargarlo, aunque ya se use la misma MDC_API_KEY.

Uso:
    python scripts/01_download_dataset.py --max-rows 500
    python scripts/01_download_dataset.py --lang en-us --max-rows 500
"""

from __future__ import annotations

import argparse
import csv
import os
import tarfile
from pathlib import Path

import requests

from common import RAW_DIR

API_BASE = "https://mozilladatacollective.com/api"

# (etiqueta de género tal como la espera GENDER_LABEL_MAP en common.py, dataset id de MDC),
# por idioma. Todos son "Common Voice Scripted Speech 26.0" ya curados por MDC
# Curators en pares macho/hembra. Antes de agregar un idioma nuevo aquí, hay
# que aceptar los términos de CADA dataset desde mozilladatacollective.com
# logueado con la cuenta dueña de MDC_API_KEY (la API no deja aceptarlos);
# entrar a https://mozilladatacollective.com/datasets/<id> de cada uno.
LANGUAGE_DATASETS: dict[str, list[tuple[str, str]]] = {
    "es-mx": [
        ("female_feminine", "cmr3zunmk00flnt07p7ai9p43"),  # CV Scripted Speech 26.0 es-MX, mujeres
        ("male_masculine", "cmr3jjevj0041nt07vb3sm35d"),  # CV Scripted Speech 26.0 es-MX, hombres
    ],
    "en-us": [
        ("female_feminine", "cmrt70j4z001qmm07nvfsmgmr"),  # CV Scripted Speech 26.0 en-US, mujeres
        ("male_masculine", "cmrt6zbgx000vmm07hfuefigk"),  # CV Scripted Speech 26.0 en-US, hombres
    ],
    "nl-nl": [
        ("female_feminine", "cmruvkoaj00b0md07fjxzw6x5"),  # CV Scripted Speech 26.0 nl-NL, mujeres
        ("male_masculine", "cmruvkf8p00ajnx07rfn0ecv9"),  # CV Scripted Speech 26.0 nl-NL, hombres
    ],
    "ar": [
        ("female_feminine", "cmrv0fgp00022nu077cdkkcny"),  # CV Scripted Speech 26.0 árabe, mujeres
        ("male_masculine", "cmrv0f62m001wnu077iwrjbbo"),  # CV Scripted Speech 26.0 árabe, hombres
    ],
}
DEFAULT_DATASETS = LANGUAGE_DATASETS["es-mx"]

AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".ogg")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lang",
        default="es-mx",
        choices=sorted(LANGUAGE_DATASETS.keys()),
        help="Qué par de datasets (ya curados por género) descargar; también nombra el manifest de salida.",
    )
    parser.add_argument("--max-rows", type=int, default=500, help="Límite total de filas en el manifest")
    return parser.parse_args()


def _get_download_url(dataset_id: str, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{API_BASE}/datasets/{dataset_id}/download", headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "downloadUrl" not in payload:
        raise RuntimeError(f"Respuesta inesperada de MDC para {dataset_id}: {payload}")
    return payload["downloadUrl"]


def _stream_clips(download_url: str, clips_dir: Path, limit: int) -> list[Path]:
    """Descomprime el .tar.gz al vuelo y guarda solo los primeros `limit` audios.

    No baja el archivo completo a disco: tarfile en modo streaming ('r|gz')
    lee y descomprime en el mismo paso que se recorre cada miembro del tar.
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    with requests.get(download_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with tarfile.open(fileobj=resp.raw, mode="r|gz") as tar:
            for member in tar:
                if len(written_paths) >= limit:
                    break
                if not member.isfile() or not member.name.lower().endswith(AUDIO_EXTENSIONS):
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                out_path = clips_dir / Path(member.name).name
                out_path.write_bytes(extracted.read())
                written_paths.append(out_path)
    return written_paths


def main() -> None:
    args = parse_args()
    token = os.environ.get("MDC_API_KEY")
    if not token:
        raise SystemExit("Falta MDC_API_KEY en el entorno (agrégalo a tu .env)")

    datasets = LANGUAGE_DATASETS[args.lang]
    manifest_path = RAW_DIR / f"manifest_{args.lang}.csv"
    per_dataset_cap = max(1, args.max_rows // len(datasets))

    rows_written = 0
    with open(manifest_path, "w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.writer(manifest_file)
        writer.writerow(["audio_path", "gender", "age", "client_id"])

        for gender_label, dataset_id in datasets:
            print(f"Descargando {dataset_id} ({gender_label})...")
            download_url = _get_download_url(dataset_id, token)
            clips_dir = RAW_DIR / args.lang / gender_label
            clip_paths = _stream_clips(download_url, clips_dir, per_dataset_cap)
            for clip_path in clip_paths:
                # Relativo a RAW_DIR (no absoluto): así el manifest no filtra
                # la ruta local de quien lo generó, y sigue siendo válido si
                # alguien más regenera training/data/raw/ en su máquina.
                writer.writerow([str(clip_path.relative_to(RAW_DIR)), gender_label, "", ""])
            rows_written += len(clip_paths)
            print(f"  {len(clip_paths)} clips guardados en {clips_dir}")

    print(f"Total: {rows_written} filas -> {manifest_path}")


if __name__ == "__main__":
    main()
