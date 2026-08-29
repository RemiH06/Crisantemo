# QuetzBeats: herramienta de análisis de voz para práctica de cispassing

## Contexto

El usuario quiere construir una herramienta que ayude a mujeres trans a practicar su voz con fines de "cispassing": un modelo da una puntuación de 0 (suena masculino) a 100 (suena femenino), donde 50 es andrógino. El requisito central es que el sistema NO se deje engañar solo por el pitch: un hombre con voz aguda debe seguir puntuando como masculino, y una mujer trans con pitch algo grave pero buena resonancia debe puntuar como femenina. Esto es un problema conocido en fonética: la percepción de género vocal depende sobre todo de los formantes (resonancia del tracto vocal), no solo de la frecuencia fundamental (F0).

Es un proyecto nuevo desde cero (carpeta de trabajo vacía). Decisiones ya acordadas con el usuario:
- Modos de uso: análisis de grabaciones subidas Y modo en vivo (near-real-time).
- Plataforma: web por ahora, backend como API HTTP separada para poder reusarse desde móvil después. Todo en entorno local, con Docker.
- Puertos: todo en el rango 9000-9999.
- Enfoque de ML: híbrido, recomendado y aceptado por el usuario. En vez de entrenar una red desde audio crudo (lo cual exigiría recolectar voces propias, con problemas éticos/de privacidad), se usan librerías de extracción acústica ya existentes (parselmouth/Praat, librosa) para sacar features interpretables (F0, formantes F1-F3, jitter/shimmer/HNR), y sobre esas features se entrena un clasificador ligero (LightGBM o regresión logística) usando un dataset público ya etiquetado por género (Mozilla Common Voice). Esto sigue la filosofía de usar herramientas existentes antes que reinventar, y reduce drásticamente la cantidad de código y datos propios necesarios.

## Estructura del repositorio

```
quetzbeats/
├── docker-compose.yml
├── .env.example
├── docs/{ARCHITECTURE.md, API.md, ETHICS_PRIVACY.md}
├── backend/                 # FastAPI, servicio de inferencia
│   ├── app/
│   │   ├── main.py, config.py, schemas.py
│   │   ├── api/routes_analysis.py, routes_stream.py, routes_health.py
│   │   ├── audio/decode.py, features.py, vad.py
│   │   ├── scoring/model_loader.py, predictor.py, feedback.py
│   │   └── streaming/session.py, aggregator.py
│   └── tests/
├── frontend/                # Vite + JS vanilla/Preact
│   └── src/{api/client.js, audio/recorder.js, components/{ScoreMeter,FeedbackPanel,UploadForm,LiveMode}.js}
├── training/                # pipeline offline, no es servicio persistente
│   └── scripts/01_download_dataset.py ... 06_export_model.py
└── models/                  # artefactos versionados (contrato training <-> backend)
    ├── quetzbeats_v1.joblib
    └── feature_schema_v1.json
```

`models/feature_schema_v1.json` es el contrato de nombres/orden de columnas entre entrenamiento e inferencia; el backend valida contra él al arrancar y falla rápido si hay desajuste. La lógica de extracción de features vive en un único lugar (`shared/acoustic_features.py` o reusada directamente por ambos) para que training e inferencia nunca diverjan.

## Stack técnico

- **Backend**: FastAPI + uvicorn (soporte nativo de WebSocket para el modo en vivo, docs OpenAPI gratis).
- **Extracción acústica**: `praat-parselmouth` (F0, formantes F1-F4, jitter, shimmer, HNR) + `librosa` (MFCCs, espectrales, resampleo). `ffmpeg`/`soundfile` para decodificar el audio webm/opus del navegador.
- **VAD**: `webrtcvad` (ligero) para no puntuar silencio en modo streaming.
- **Clasificador**: `scikit-learn` (LogisticRegression, baseline interpretable) o `lightgbm`. Entrenado sobre el vector de features, no sobre audio crudo.
- **Serialización**: `joblib`; opcional exportar a ONNX (`skl2onnx`) pensando en reuso futuro desde móvil.
- **Frontend**: Vite + JS vanilla/Preact, `MediaRecorder`/`AudioWorklet` para captura de audio.
- **Dataset de entrenamiento**: Mozilla Common Voice (subset español vía Hugging Face `datasets`, campo `gender` en metadata, licencia CC0). Documentar en `docs/ETHICS_PRIVACY.md` que el dataset refleja percepción binaria promedio, no identidad real de nadie.

## API

- `POST /api/v1/analyze` (multipart, sube audio) → `{score, confidence, features: {f0_mean_hz, f1_mean_hz, f2_mean_hz, f2_f1_diff_hz, jitter, shimmer, hnr_db, intonation_variation, ...}, feedback: {summary, tone: "supportive", suggestions}, meta}`. Nunca solo un número: siempre desglose + feedback de apoyo, nunca tono de "aprobado/reprobado".
- `WS /api/v1/stream`: cliente envía chunks PCM cada ~300ms; servidor acumula ventana de 2-3s con solape (los formantes necesitan señal suficiente para estabilizarse), filtra silencio con VAD, y emite `score_update` con `score` y `score_smoothed` (EMA) cada 1-2s para que el medidor no salte.
- `GET /health`, `GET /api/v1/model-info`.

## Pipeline de entrenamiento (`training/scripts/`)

1. `01_download_dataset.py`: descarga Common Voice (subset ES, luego posible EN para volumen).
2. `02_prepare_labels.py`: filtra género válido, balancea clases, split train/val/test estratificado.
3. `03_extract_features.py`: parselmouth + librosa → parquet con columnas fijas (`feature_schema_v1.json`).
4. `04_train_model.py`: LightGBM/LogReg + StratifiedKFold + grid pequeño de hiperparámetros.
5. `05_evaluate_model.py`: accuracy, F1, matriz de confusión, MAE del score continuo, e **importancia de features (SHAP)** — criterio de aceptación clave: si F0 domina >60-70% de la importancia, hay que rebalancear/regularizar, porque es exactamente el sesgo que el usuario pidió evitar.
6. `06_export_model.py`: calibra probabilidad a score 0-100, exporta `.joblib` (+ opcional ONNX) a `models/`.

## Docker y puertos

| Servicio | Puerto host | Notas |
|---|---|---|
| frontend | 9000 | Vite dev / nginx |
| backend | 9001 | FastAPI, REST + WS en el mismo puerto |
| training | 9002 (opcional, Jupyter) | perfil `training` en docker-compose, bajo demanda, nunca junto a los servicios persistentes |

## Fases de implementación

0. Andamiaje: estructura de carpetas, `docker-compose.yml` esqueleto, Dockerfiles mínimos.
1. Pipeline de entrenamiento offline con subset pequeño de Common Voice → modelo v1 + reporte de evaluación (verificar que no dependa solo de F0).
2. Backend de inferencia: `features.py`/`predictor.py`/`model_loader.py` + `POST /analyze` + `feedback.py`.
3. Frontend básico: subir/grabar audio, ver score y feedback.
4. Modo en vivo: WebSocket + streaming/session.py + LiveMode.js.
5. Endurecimiento: manejo de errores (audio corto/sin voz/corrupto), logging, `docs/API.md`, revisión final de privacidad (no persistir audio por defecto, mensaje visible al usuario).

## Verificación

- Tests unitarios de `features.py` con tonos sintéticos (`numpy.sin` a frecuencia conocida) validando que F0 se detecta correctamente.
- Métricas del modelo (accuracy, F1, MAE, SHAP) contra test set separado; el criterio más importante es que la importancia de features no esté dominada solo por F0.
- Tests de API con `TestClient` de FastAPI sobre audios fixture, validando `0 <= score <= 100`.
- Prueba manual end-to-end en navegador (permiso de micrófono, grabar, subir, ver resultado) en Chrome y Firefox.
- Prueba manual del modo streaming con un script cliente WS enviando un WAV trozado en chunks.
- `docker compose up` levanta frontend+backend sanos (healthcheck OK); `docker compose --profile training run training ...` corre el pipeline sin afectar los servicios persistentes.

## Archivos críticos

- `backend/app/audio/features.py` (compartido con training) — extracción F0/formantes/jitter/shimmer/HNR, punto donde training e inferencia deben coincidir exactamente.
- `training/scripts/04_train_model.py` y `05_evaluate_model.py` — entrenamiento y validación de que el modelo no dependa solo de F0.
- `backend/app/api/routes_stream.py` + `backend/app/streaming/session.py` — ventaneo/buffer del modo en vivo.
- `models/feature_schema_v1.json` — contrato de columnas entre training y backend.
- `docker-compose.yml` — puertos 9000-9999 y separación de servicios persistentes vs. pipeline bajo demanda.
