# API

`POST /api/v1/analyze`, `GET /health` y `GET /api/v1/model-info` ya están implementados en `backend/app/api/` y corresponden a lo descrito aquí. `WS /api/v1/stream` (modo en vivo) sigue siendo diseño planeado, Fase 4 no ha empezado.

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
    "suggestions": [
      { "text": "string", "kind": "acierto" }
    ]
  },
  "meta": {
    "voiced_seconds": 0,
    "duration_seconds": 0
  }
}
```

Los nombres de `features` deben coincidir exactamente con `models/feature_schema_v1.json` y con `shared/acoustic_features.FEATURE_NAMES`; el backend valida este contrato al arrancar.

Cada `suggestion.kind` es uno de `acierto` (verde, algo que ya va bien), `sugerencia` (azul, tip accionable), `advertencia` (amarillo, algo a tener en cuenta de la grabación, no del habla en sí) o `problema` (rojo, un desajuste real que vale la pena trabajar). Nunca es un veredicto de "aprobado/reprobado" (ver `docs/ETHICS_PRIVACY.md`); el frontend los pinta con símbolo + color en vez de una lista plana (`frontend/src/styles/theme.css`, clases `.suggestion-*`).

**Límites del archivo subido** (`backend/app/audio/decode.py`): 20MB de tamaño, 2 minutos de duración decodificada. Generosos a propósito, ninguna grabación de práctica real se les acerca; son solo para no procesar una subida absurda por accidente o abuso.

**Errores esperados** (todos como `{"detail": "mensaje en tono de apoyo"}`, ya implementados):

| Status | Causa |
|---|---|
| `400` | Archivo vacío, más grande de 20MB, decodifica a más de 2 minutos, o no se pudo decodificar como audio (formato no soportado, corrupto). |
| `422` | Menos de `MIN_VOICED_SECONDS` (0.3s) de voz sonora detectada. |
| `422` | La grabación mezcla dos registros de tono muy distintos (ej. empezar grave y cambiar a agudo a la mitad); el promedio no representaría a ninguna de las dos voces. Ver `shared/acoustic_features/features.py::_has_register_switch`. |
| `500` | Error inesperado del servidor. |

El formato de error es el mismo para los tres casos: un solo campo `detail` con el mensaje completo ya redactado en tono de apoyo (no un código separado ni un campo por error), porque el frontend lo muestra tal cual sin reinterpretarlo (ver `frontend/src/api/client.js`).

### `WS /api/v1/stream`

Modo en vivo. Implementado (`backend/app/api/routes_stream.py` + `backend/app/streaming/session.py`); ver `docs/ARCHITECTURE.md` por qué se descartó Rust/WASM y se quedó todo del lado del backend (mismo `shared/acoustic_features`, cero riesgo de que diverja del análisis por REST).

**Handshake**: el primer mensaje del cliente debe ser texto JSON `{"sample_rate": N}` (la frecuencia real de captura del navegador, normalmente 44100 o 48000, no hace falta que sea 16000). Si no llega así, el servidor cierra la conexión con código `1002`.

**Después del handshake**: el cliente manda solo frames binarios, PCM Int16 mono little-endian, de forma continua (no hace falta que el cliente los trocee a un tamaño exacto). El servidor:

1. Acumula todo en un buffer propio (el cliente no lleva ventaneo, toda esa lógica vive en `StreamingSession`) y se queda solo con los últimos `WINDOW_SECONDS` (2.5s).
2. Cada vez que se acumularon `STEP_SECONDS` (1.2s) de audio nuevo, resamplea a 16kHz si hace falta, normaliza amplitud (misma función que usa `/analyze`) y corre `extract_features` sobre esa ventana.
3. Si la ventana no tiene suficiente voz sonora o parece mezclar dos tonos de voz (`InsufficientVoiceError`/`UnstableVoiceError`, los mismos chequeos de `/analyze`), simplemente no manda nada esa vuelta y espera a la siguiente ventana. No hay VAD aparte (`webrtcvad`): se reusa el mismo chequeo de voz sonora que ya existe, evita una dependencia que además no compila en algunas máquinas (ver `CLAUDE.md`).
4. Si hay suficiente voz, emite `score_update` con `score` (crudo de esa ventana) y `score_smoothed` (EMA, `EMA_ALPHA=0.35`, para que el medidor no salte de golpe).

```json
{
  "type": "score_update",
  "score": 0,
  "score_smoothed": 0,
  "features": { "...": "mismo desglose que /analyze, sin voiced_seconds/duration_seconds" }
}
```

El cliente (`frontend/src/audio/liveStream.js`) captura con `ScriptProcessorNode` (no `AudioWorkletNode`: deprecado pero funciona en todos los navegadores actuales sin necesitar cargar un archivo de worklet aparte) y grafica con canvas vanilla (`frontend/src/components/liveGraph.js`), no React.

### `GET /health`

Healthcheck simple para Docker/orquestación. `200 OK` si el servicio está arriba y el modelo cargó correctamente.

### `GET /api/v1/model-info`

Metadata del modelo cargado: versión, fecha de entrenamiento, métricas de evaluación relevantes (por ejemplo el peso combinado de features de F0 de `eval_v1.md`), para que el frontend o cualquier cliente pueda mostrar de qué modelo viene un score. Público, sin autenticación: no expone nada sensible (nombres de features y versión del modelo, no datos de ninguna persona), y el proyecto no tiene infraestructura de autenticación todavía. Si eso cambia (por ejemplo, al agregar historial de progreso por sesión), revisar esta decisión.
