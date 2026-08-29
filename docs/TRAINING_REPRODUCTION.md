# Cómo reproducir el pipeline de entrenamiento y el reporte de evaluación

Esto documenta exactamente los pasos que se corrieron para llegar a `training/data/reports/eval_v1.md`. Sirve tanto para repetirlo con el dataset sintético de prueba como, en una máquina con internet completo, para correrlo con Mozilla Common Voice de verdad.

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

## 2A. Con el dataset real (Common Voice) — requiere internet

```bash
# Opcional: si tu versión/región del dataset pide autenticación
export HF_TOKEN=tu_token_de_huggingface

cd training
python scripts/01_download_dataset.py --lang es --max-rows 20000
python scripts/02_prepare_labels.py --lang es
```

## 2B. Con el dataset sintético de prueba — sin internet

Este es el que se usó para producir `eval_v1.md` en el entorno donde se escribió el proyecto, porque no había acceso a Common Voice ahí. Genera voces sintéticas (pulsos glotales filtrados por resonadores de formantes) separables tanto por pitch como por resonancia, solo para probar que el pipeline funciona de punta a punta. **No reemplaza entrenar con voces reales.**

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

## 4. Bug encontrado y arreglado en el camino

`02_prepare_labels.py` usaba `df.groupby("label").apply(...)` para balancear las clases. En pandas 3.0 esto cambió de comportamiento y descarta la columna de agrupación del resultado (`KeyError: 'label'` más adelante). Se arregló reemplazándolo por una lista por comprensión + `pd.concat`, que no depende de ese comportamiento:

```python
balanced_parts = [
    group.sample(n=minority_count, random_state=RANDOM_SEED) for _, group in df.groupby("label")
]
df = pd.concat(balanced_parts, ignore_index=True)
```

Si en tu máquina usas una versión de pandas distinta, este fix ya está aplicado en el repo, no hace falta hacer nada extra.

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

Los mismos scripts, pero corriendo dentro del contenedor `training` (perfil `training` de docker-compose, para que nunca se levante junto a los servicios persistentes):

```bash
docker compose --profile training run --rm training python scripts/01_download_dataset.py --lang es
docker compose --profile training run --rm training python scripts/02_prepare_labels.py --lang es
docker compose --profile training run --rm training python scripts/03_extract_features.py
docker compose --profile training run --rm training python scripts/04_train_model.py
docker compose --profile training run --rm training python scripts/05_evaluate_model.py
docker compose --profile training run --rm training python scripts/06_export_model.py
```

Nota: el entorno donde se escribió este proyecto no tuvo acceso a Docker Hub tampoco, así que esta ruta no se pudo probar ahí; sí debería funcionar en una máquina con internet normal.
