# Cómo reproducir el pipeline de entrenamiento y el reporte de evaluación

Esto documenta exactamente los pasos que se corrieron para llegar a `training/data/reports/eval_v1.md`. Sirve tanto para repetirlo con el dataset sintético de prueba como, en una máquina con internet completo, para correrlo con Mozilla Common Voice de verdad.

**Estado actual: `eval_v1.md` ya viene de una corrida con datos reales** (Common Voice 26.0, español mexicano, 500 clips: 350 train / 75 val / 75 test), no del dataset sintético. Resultado: 94.67% accuracy, F1 0.9429, peso combinado de F0 de 33.7% (bien debajo del 60% de advertencia). La sección 2A de abajo documenta cómo se descargó.

## 1. Preparar el entorno

No hace falta Docker para iterar rápido en local; un entorno virtual de Python alcanza (los mismos scripts corren igual dentro del contenedor `training`, ver `training/Dockerfile`).

```bash
cd crisantemo
python3 -m venv .venv
source .venv/bin/activate

# Paquete compartido de extracción de features (editable, para que los cambios
# en shared/acoustic_features se reflejen sin reinstalar)
pip install -e shared/

# Dependencias del pipeline de entrenamiento
pip install -r training/requirements.txt
```

## 2A. Con el dataset real (Common Voice, vía Mozilla Data Collective) — requiere internet

**Importante:** desde octubre de 2025, Mozilla movió la distribución de Common Voice de Hugging Face a su propia plataforma, [Mozilla Data Collective](https://mozilladatacollective.com). El mirror en Hugging Face (`mozilla-foundation/common_voice_17_0` y similares) quedó vacío a propósito, no es un problema de permisos ni de red: si `01_download_dataset.py` alguna vez usó `datasets.load_dataset` de Hugging Face, ese código ya no aplica y fue reemplazado por completo.

Pasos previos (una sola vez, desde el navegador, con tu cuenta):

1. Crea una cuenta en [mozilladatacollective.com](https://mozilladatacollective.com).
2. Busca el dataset que quieras usar y entra a su página para aceptar los términos de uso ahí mismo (la API no deja aceptarlos, tiene que ser desde el sitio). Por defecto el script usa dos datasets curados por "MDC Curators": Common Voice Scripted Speech 26.0, español mexicano, ya filtrados por género autorreportado y solo audio validado:
   - Mujeres: `https://mozilladatacollective.com/datasets/cmr3zunmk00flnt07p7ai9p43`
   - Hombres: `https://mozilladatacollective.com/datasets/cmr3jjevj0041nt07vb3sm35d`
3. Genera un API key en tu perfil → `credentials`.

```bash
# Agrega esto a tu .env (no lo pegues en la terminal ni en el chat con el asistente)
# MDC_API_KEY=tu_api_key

cd training
python scripts/01_download_dataset.py --max-rows 500
python scripts/02_prepare_labels.py --lang es-mx
```

`01_download_dataset.py` transmite y descomprime cada `.tar.gz` al vuelo (sin bajar el archivo completo a disco) y se detiene apenas junta `--max-rows / 2` clips de cada género; los datasets completos pesan ~1.8GB y ~2GB cada uno, así que para una corrida de validación no hace falta bajarlos enteros. Si más adelante se quiere entrenar con más datos, basta con subir `--max-rows` (a costa de más tiempo de descarga).

Si se quiere usar un dataset distinto de MDC (otro idioma, otra versión), hay que editar `DEFAULT_DATASETS` en el script con el (etiqueta de género, dataset id) correspondiente; el id es el que aparece en la URL de la página del dataset.

## 2B. Con el dataset sintético de prueba — sin internet

Este es el que se usó para la primera validación mecánica del pipeline, antes de tener acceso a Common Voice real (`eval_v1.md` ya no viene de aquí, ver nota al inicio de este documento). Genera voces sintéticas (pulsos glotales filtrados por resonadores de formantes) separables tanto por pitch como por resonancia, solo para probar que el pipeline funciona de punta a punta. **No reemplaza entrenar con voces reales.**

```bash
cd training
python scripts/_dev_synthetic_dataset.py --n-per-class 150
python scripts/02_prepare_labels.py --lang synthetic_dev
```

## 3. El resto del pipeline es igual en ambos casos

```bash
python scripts/03_extract_features.py
python scripts/04_train_model.py
python scripts/05_evaluate_model.py
python scripts/06_export_model.py
```

- `03_extract_features.py` extrae el vector de features (pitch, formantes, jitter/shimmer/HNR) de cada audio usando `acoustic_features` (el mismo módulo que usa el backend).
- `04_train_model.py` entrena y compara una regresión logística contra LightGBM con validación cruzada de 5 folds, y guarda el mejor en `training/data/models/crisantemo_v1_raw.joblib`.
- `05_evaluate_model.py` genera el reporte: accuracy, F1, matriz de confusión, MAE del score continuo, e importancia de cada feature. Esto es lo que escribe `training/data/reports/eval_v1.md`. El chequeo importante que hace es sumar la importancia de las tres features de F0 (`f0_mean_hz`, `f0_std_hz`, `f0_range_semitones`); si superan 60% del total, avisa que el modelo se está apoyando demasiado en el pitch.
- `06_export_model.py` calibra el modelo (para que el score 0-100 sea confiable, no solo la clasificación binaria) y lo copia a `models/crisantemo_v1.joblib` en la raíz del repo, junto con `models/feature_schema_v1.json`.

## 4. Cosas encontradas y arregladas en el camino

**4.1. Bug de pandas 3.0.** `02_prepare_labels.py` usaba `df.groupby("label").apply(...)` para balancear las clases. En pandas 3.0 esto cambió de comportamiento y descarta la columna de agrupación del resultado (`KeyError: 'label'` más adelante). Se arregló reemplazándolo por una lista por comprensión + `pd.concat`, que no depende de ese comportamiento:

```python
balanced_parts = [
    group.sample(n=minority_count, random_state=RANDOM_SEED) for _, group in df.groupby("label")
]
df = pd.concat(balanced_parts, ignore_index=True)
```

Si en tu máquina usas una versión de pandas distinta, este fix ya está aplicado en el repo, no hace falta hacer nada extra.

**4.2. Common Voice se movió fuera de Hugging Face.** La primera versión de `01_download_dataset.py` usaba `datasets.load_dataset("mozilla-foundation/common_voice_17_0", ...)`. Al intentarlo con datos reales, el dataset apareció vacío en Hugging Face sin importar el token usado; resultó ser que Mozilla movió la distribución completa de Common Voice a su propia plataforma (Mozilla Data Collective) en octubre de 2025, y el mirror en HF se quedó sin archivos a propósito. El script se reescribió por completo para usar la API de Mozilla Data Collective en su lugar (ver sección 2A). De paso, esto también hizo innecesarias las dependencias `datasets` y `huggingface_hub` en `training/requirements.txt` (se quitaron).

## 5. Prueba de estrés manual (opcional, pero recomendada)

Para confirmar que el modelo usa resonancia y no solo pitch, se generaron cuatro voces sintéticas de control cruzando pitch y formantes en direcciones opuestas, y se les pidió el score al modelo crudo (antes de calibrar):

```bash
cd training
python3 - <<'EOF'
import sys, joblib, numpy as np
sys.path.insert(0, "scripts")
from acoustic_features import extract_features
from scripts._dev_synthetic_dataset import synth_vowel, SAMPLE_RATE

model = joblib.load("data/models/crisantemo_v1_raw.joblib")
rng = np.random.default_rng(123)

casos = {
    "grave + formantes masculinos": dict(f0=100, formants=(730, 1090, 2440)),
    "agudo + formantes femeninos":  dict(f0=220, formants=(850, 1650, 2950)),
    "agudo pero formantes masculinos": dict(f0=220, formants=(730, 1090, 2440)),
    "grave pero formantes femeninos":  dict(f0=110, formants=(850, 1650, 2950)),
}
for nombre, params in casos.items():
    signal = synth_vowel(params["f0"], params["formants"], 90, rng)
    feats = extract_features(signal, SAMPLE_RATE)
    x = feats.to_vector().reshape(1, -1)
    score = model.predict_proba(x)[0, 1] * 100
    print(f"{nombre}: {score:.1f}")
EOF
```

## 6. Con Docker, en vez de un venv

Los mismos scripts, pero corriendo dentro del contenedor `training` (perfil `training` de docker-compose, para que nunca se levante junto a los servicios persistentes). El servicio `training` carga `.env` (incluye `MDC_API_KEY` si lo agregaste ahí):

```bash
docker compose --profile training run --rm training python scripts/01_download_dataset.py --max-rows 500
docker compose --profile training run --rm training python scripts/02_prepare_labels.py --lang es-mx
docker compose --profile training run --rm training python scripts/03_extract_features.py
docker compose --profile training run --rm training python scripts/04_train_model.py
docker compose --profile training run --rm training python scripts/05_evaluate_model.py
docker compose --profile training run --rm training python scripts/06_export_model.py
```
