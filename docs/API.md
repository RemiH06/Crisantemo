# API (diseño planeado)

Este documento describe el diseño de la API acordado en la planeación original del proyecto (`docs/PLAN.md`). Es el contrato al que debe apegarse la implementación de Fase 2, todavía sin construir. Nada de lo descrito aquí está implementado hoy; cuando `backend/app/api/` exista de verdad, este documento debe actualizarse para reflejar la implementación real, no quedarse como aspiración.

## Principios de diseño

- El backend siempre expone el score numérico crudo (0-100) junto con el desglose completo de features, sin suavizarlo. Ver "Diseño de puntuación" en `docs/ARCHITECTURE.md`.
- La respuesta nunca es solo un número: siempre incluye desglose de features y retroalimentación en lenguaje llano, con tono de apoyo, nunca de "aprobado/reprobado".
- No se persiste audio (ver `docs/ETHICS_PRIVACY.md`).

## Endpoints REST

### `POST /api/v1/analyze`

Sube un audio completo (multipart) y recibe el análisis.

**Request**: multipart/form-data con el archivo de audio (webm/opus, wav, u otro formato soportado por `ffmpeg`/`soundfile`).

**Response** (`200 OK`):

```json
{
  "score": 0,
  "confidence": 0,
  "features": {
    "f0_mean_hz": 0,
    "f0_std_hz": 0,
    "f0_range_semitones": 0,
    "f1_mean_hz": 0,
    "f2_mean_hz": 0,
    "f3_mean_hz": 0,
    "f2_f1_diff_hz": 0,
    "f3_f2_diff_hz": 0,
    "jitter_local_pct": 0,
    "shimmer_local_pct": 0,
    "hnr_db": 0,
    "spectral_centroid_mean_hz": 0
  },
  "feedback": {
    "summary": "string",
    "tone": "supportive",
    "suggestions": ["string"]
  },
  "meta": {
    "voiced_seconds": 0,
    "duration_seconds": 0
  }
}
```

Los nombres de `features` deben coincidir exactamente con `models/feature_schema_v1.json` y con `shared/acoustic_features.FEATURE_NAMES`; el backend valida este contrato al arrancar.

**Errores esperados**: audio demasiado corto, sin voz detectada (VAD no encuentra segmentos hablados), o archivo corrupto/formato no soportado. El manejo explícito de estos casos es trabajo de Fase 5 (endurecimiento), pero el contrato de la respuesta de error debe quedar definido en Fase 2.

### `WS /api/v1/stream`

Modo en vivo. El cliente envía chunks de audio PCM cada ~300ms. El servidor:

1. Acumula una ventana de 2-3 segundos con solape (los formantes necesitan señal suficiente para estabilizarse).
2. Filtra silencio con VAD (`webrtcvad`) para no puntuar silencio.
3. Emite un mensaje `score_update` con `score` (crudo) y `score_smoothed` (EMA) cada 1-2 segundos, para que el medidor no salte de golpe.

```json
{
  "type": "score_update",
  "score": 0,
  "score_smoothed": 0,
  "features": { "...": "mismo desglose que /analyze" }
}
```

Este endpoint depende de la decisión de arquitectura de Fase 4 documentada en `docs/ARCHITECTURE.md` (posible extracción de features en el navegador vía Rust/WASM en vez de solo en el backend); el contrato exacto de mensajes puede cambiar cuando esa fase arranque.

### `GET /health`

Healthcheck simple para Docker/orquestación. `200 OK` si el servicio está arriba y el modelo cargó correctamente.

### `GET /api/v1/model-info`

Metadata del modelo cargado: versión, fecha de entrenamiento, métricas de evaluación relevantes (por ejemplo el peso combinado de features de F0 de `eval_v1.md`), para que el frontend o cualquier cliente pueda mostrar de qué modelo viene un score.

## Pendiente de decidir en Fase 2

- Formato exacto de los mensajes de error (código, mensaje, campo afectado).
- Límites de tamaño/duración de audio aceptados en `/analyze`.
- Si `/model-info` requiere autenticación o es público.
