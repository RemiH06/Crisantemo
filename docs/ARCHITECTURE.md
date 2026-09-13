# Arquitectura de Crisantemo

## Objetivo

Dar una puntuación de 0 (percepción masculina) a 100 (percepción femenina) a partir de una grabación o audio en vivo, basada en features acústicas interpretables y no solo en el tono (pitch). El sistema debe reconocer una voz aguda masculina como masculina, y una voz algo grave con buena resonancia femenina como femenina.

## Piezas del repositorio

- `shared/acoustic_features/`: paquete Python instalable que extrae el vector de features de una señal de audio. Es el único lugar donde vive esta lógica; tanto el pipeline de entrenamiento como el backend lo importan, así nunca hay dos implementaciones que puedan desalinearse.
- `training/`: scripts que producen el modelo (`.joblib`) a partir de un dataset público etiquetado por género. Se corre bajo demanda, no es un servicio persistente.
- `backend/`: API FastAPI que carga el modelo entrenado y responde puntuaciones (grabación completa vía REST, o en vivo vía WebSocket).
- `frontend/`: interfaz web (Vite) que consume el backend.
- `models/`: artefacto del modelo (`crisantemo_v1.joblib`) + `feature_schema_v1.json`, el contrato de nombres/orden de columnas entre `training` y `backend`. El backend valida este contrato al arrancar y falla rápido si no coincide con `acoustic_features.FEATURE_NAMES` actual.

## Vector de features (estado actual, `shared/acoustic_features/features.py`)

| Feature | Qué mide |
|---|---|
| `f0_mean_hz`, `f0_std_hz`, `f0_range_semitones` | Pitch (frecuencia fundamental): promedio, variabilidad y rango de tono |
| `f1_mean_hz`, `f2_mean_hz`, `f3_mean_hz` | Formantes 1-3: resonancias del tracto vocal, el factor que más pesa en la percepción de género de una voz |
| `f2_f1_diff_hz`, `f3_f2_diff_hz` | Espaciamiento entre formantes, relacionado con el tamaño efectivo del tracto vocal |
| `jitter_local_pct`, `shimmer_local_pct` | Micro-variaciones ciclo a ciclo en frecuencia y amplitud (textura/estabilidad de la voz) |
| `hnr_db` | Relación armónico-ruido (claridad de la voz) |
| `spectral_centroid_mean_hz` | Brillo espectral general, feature complementaria |

Además se calculan `voiced_seconds` y `duration_seconds` como metadata de calidad de la señal (no entran al vector que ve el modelo, pero acompañan la respuesta).

## Diseño de puntuación: número crudo vs. retroalimentación

El backend siempre calcula y expone el score numérico crudo (0-100) más el desglose completo de features, sin suavizarlo ni "endulzarlo": es el dato con el que se puede graficar progreso, comparar grabaciones, y hacer los cálculos del modelo. La capa de retroalimentación (texto dirigido a la persona usuaria) es una capa separada que interpreta ese número de forma constructiva y de apoyo. El número y el mensaje humano son cosas distintas a propósito.

## Puertos y Docker

| Servicio | Puerto host |
|---|---|
| frontend | 9000 |
| backend | 9001 |
| training (bajo demanda, perfil `training`) | 9002 |

## Estado actual

**Fase 0 (andamiaje): completada.**
- Estructura de carpetas creada.
- `docker-compose.yml` validado (`docker compose config` corre sin errores) con los tres servicios y sus puertos, y con `name: crisantemo` explícito.
- Dockerfiles de `backend/`, `training/` y `frontend/` escritos.
- `.env.example` y `.gitignore`.
- `shared/acoustic_features` implementado y probado con un tono sintético.

**Fase 1 (pipeline de entrenamiento): completa, ya entrenado con datos reales.**
- Los 6 scripts (`01_download_dataset.py` a `06_export_model.py`) corrieron de punta a punta con datos reales.
- **Descubrimiento importante:** Common Voice se movió de Hugging Face a Mozilla Data Collective en octubre de 2025; el mirror en HF quedó vacío a propósito (no es un problema de red ni de permisos). `01_download_dataset.py` se reescribió para usar la API REST de MDC (`MDC_API_KEY`) en vez de `datasets.load_dataset`. Transmite y descomprime cada `.tar.gz` al vuelo, sin bajar el archivo completo a disco, deteniéndose apenas junta el número de filas pedido. Ver `docs/TRAINING_REPRODUCTION.md` sección 4.2 para el detalle.
- Dataset usado: dos datasets curados por "MDC Curators", Common Voice Scripted Speech 26.0, español mexicano, ya filtrados por género autorreportado y solo audio validado (≥1 upvote, 0 downvotes), CC0-1.0, más 800 ejemplos sintéticos decorrelacionados (ver abajo). 5,800 clips en total (4,060 train / 870 val / 870 test).
- Entrenamiento: LightGBM ganó sobre logreg en CV. Evaluación sobre el test set real: **97.47% accuracy, F1 0.9749**, matriz de confusión `[[419, 15], [7, 428]]`.
- El peso combinado de las features de F0 quedó en **32.5%**, bien debajo del umbral de advertencia (60%).
- `docker-compose.yml`: se le agregó `env_file: .env` al servicio `training` (no lo tenía; sin eso `MDC_API_KEY` nunca le habría llegado al contenedor).

### Hallazgo importante, sin resolver: el modelo se sigue dejando engañar por el tono en voz actuada real

Se probó con dos grabaciones reales de la misma persona (voz masculina de base, una actuando tono agudo y otra tono grave, sin trabajar resonancia): la aguda puntuó 99.7/100 y la grave 2.0/100, a pesar de que la grave tenía formantes objetivamente más "grandes" (más asociados a resonancia femenina) que la aguda. Esto va directo en contra del principio central del proyecto para este caso puntual.

Se intentaron dos cosas y ninguna lo arregló (detalle completo, con números, en `docs/TRAINING_REPRODUCTION.md` secciones 4.3-4.4):
1. **10x más datos reales** (500 → 5,000 clips): empeoró el problema. Hipótesis: en voz real, tono y resonancia van correlacionados de forma natural, así que más datos reales solo refuerza ese atajo.
2. **Mezclar 800 ejemplos sintéticos decorrelacionados** (`training/scripts/_dev_synthetic_decorrelated.py`, tono y formantes variando de forma independiente, etiquetados por formantes): el modelo llegó a 100% de accuracy en la prueba de estrés automática sobre esos mismos ejemplos sintéticos (ver el chequeo nuevo en `05_evaluate_model.py`), pero eso no generalizó a la grabación real.

Razón de fondo, ya cuantificada con datos (ver `training/notebooks/feature_analysis.ipynb`): en este dataset, F0 por sí solo tiene AUC 0.97 clasificando género (casi perfecto), mientras que los formantes por sí solos tienen AUC 0.57-0.73 (apenas mejor que azar). No es que tono y resonancia vayan fuertemente correlacionados (la correlación real es débil, r=0.10-0.37); es que los formantes, calculados como promedio simple sobre toda la grabación, casi no separan las clases por sí solos en este dataset. Además, las grabaciones de tono agudo actuado están literalmente fuera del rango de F0 que el modelo vio en entrenamiento (casi no pasa de 300 Hz), así que ahí el modelo extrapola, no elige ignorar los formantes.

**Actualización, misma sesión, más tarde:** se encontró por qué la aumentación sintética (punto 2 arriba) no transfería: los formantes sintéticos eran 2 valores fijos exactos, ni siquiera dentro del rango real, que el modelo podía usar como huella digital de "esto es sintético" en vez de aprender el patrón real. Al muestrear formantes de una distribución calibrada con los datos reales (en vez de valores fijos), **sí hubo mejora real**: las voces agudas actuadas bajaron de ~99/100 a 58-71/100 (de "casi seguro femenino" a "ambiguo"), a costa de accuracy general (98% → 85%) porque el modelo ya no puede memorizar formantes exactos. Sigue sin resolverse del todo (no se voltean a masculino), y se confirmó con una grabación nueva en producción (voz descrita como "muy fingida", dio 97%). Detalle completo con todos los intentos (incluida la normalización de amplitud, que no tuvo efecto porque las 12 features ya son invariantes a volumen) en `docs/TRAINING_REPRODUCTION.md` secciones 4.6-4.8, que es donde continúa esta investigación.

**Segunda actualización, misma sesión:** pesar los ejemplos adversariales 5x en el entrenamiento (`--adversarial-weight` en `04_train_model.py`) dio otra mejora real, después de encontrar y arreglar dos bugs en `06_export_model.py`: la calibración (`CalibratedClassifierCV`) reentrenaba el modelo desde cero sin el peso, y aun corrigiendo eso, calibrar con `cv=5` diluía el efecto del peso al reentrenar 5 copias con menos datos cada una. Se cambió a calibrar sin reentrenar (`FrozenEstimator` sobre el split de val, el reemplazo de `cv="prefit"` en scikit-learn >= 1.6). Resultado: una de las 5 grabaciones de prueba **ya cruza correctamente a masculino** (antes 58.6/100, ahora 33.7/100); las demás mejoraron pero no todas cruzan. El modelo actual (`models/crisantemo_v1.joblib`) es 5,000 reales + 3,000 sintéticos con formantes variables, entrenado con peso adversarial. Detalle completo en `docs/TRAINING_REPRODUCTION.md` secciones 4.6-4.9. Caminos identificados para retomar: más ejemplos sintéticos, correlacionar la severidad de jitter/shimmer/entonación con el género (no solo con el individuo), pitch-normalizar antes de medir formantes (idea original, pausada), o considerar una arquitectura híbrida que le garantice un piso de peso a las features de resonancia en vez de dejarlo 100% aprendido.

**Tercera actualización, sesión posterior:** se subió el peso adversarial de 5x a 10x (barrido completo 5-20 en `docs/TRAINING_REPRODUCTION.md` sección 4.10), con mejora clara y monótona en la prueba automática (accuracy en adversariales sintéticos 85.5%→91.7%, costo de 81.7%→79.5% en accuracy general). Modelo reexportado a `models/crisantemo_v1.joblib` con peso 10. Se había encontrado un riesgo al verificar con la prueba de estrés manual (sección 5): Praat mide mal F1 en voz sintética grave (F0=100Hz) con formantes masculinos, y subir el peso adversarial hace que el modelo dependa más de `f2_f1_diff_hz`, amplificando ese ruido hacia el lado femenino en un caso que debería ser masculino sin ambigüedad.

**Cuarta actualización, confirmado y revertido:** el usuario probó el modelo con peso 10 contra voz real y confirmó el riesgo de la actualización anterior, peor de lo esperado: hasta una voz masculina de manual (sin ambigüedad) puntuaba ~57/100. Se revirtió a `--adversarial-weight 5` (el estado validado de la sección 4.9). Subir el peso adversarial a secas queda descartado como camino para arreglar "aguda actuada" (el único caso de prueba que nunca cruzó a masculino): el costo en casos fáciles es real. Detalle completo en `docs/TRAINING_REPRODUCTION.md` sección 4.11.

## Fase 4 (modo en vivo): implementada

Para el modo en vivo se descartó Phoenix/Elixir (resolvería un problema de concurrencia masiva que este proyecto no tiene, y de todas formas necesitaría llamar a un servicio Python aparte porque parselmouth/librosa no existen en Elixir).

También se descartó, por ahora, compilar `shared/acoustic_features` a WASM con Rust para correr la extracción directo en el navegador. Esa ruta seguía siendo atractiva por privacidad (el audio nunca saldría del cliente) y porque resolvía de raíz la pregunta de cómo graficar en vivo, pero el costo era real: parselmouth envuelve Praat (C), no hay puerto directo a Rust, habría que reimplementar F0 (autocorrelación/YIN) y formantes (LPC) desde cero y validar que produce los mismos números que la versión Python, para no romper el contrato de `models/feature_schema_v1.json`. El usuario decidió la "ruta simple" en su lugar: el backend sigue siendo el único que analiza audio, solo se le agregó un canal WebSocket. Esto se puede revisar más adelante si la privacidad de streaming en vivo se vuelve una prioridad mayor; no se descartó la idea, solo se pospuso.

**Implementación real:**

- **Backend** (`backend/app/streaming/session.py` + `backend/app/api/routes_stream.py`, montado en `main.py`): `WS /api/v1/stream`. El cliente manda un handshake JSON (`{"sample_rate": N}`), luego frames binarios PCM Int16 mono continuos. `StreamingSession` mantiene una ventana deslizante de `WINDOW_SECONDS=2.5` con paso `STEP_SECONDS=1.2`, resamplea a 16kHz y normaliza amplitud igual que `/analyze`, corre `extract_features` sobre cada ventana, reusa `InsufficientVoiceError`/`UnstableVoiceError` (sin `webrtcvad` aparte) para saltarse ventanas sin voz sonora o con salto de registro, y suaviza el score con EMA (`EMA_ALPHA=0.35`) antes de mandar `score_update` por el socket. Protocolo completo documentado en `docs/API.md`.
- **Frontend** (`frontend/src/audio/liveStream.js` + `frontend/src/components/liveGraph.js`, integrados en `app.js` como el estado `"live"`): captura con `ScriptProcessorNode` (no `AudioWorkletNode`, deprecado pero universal y sin archivo de worklet aparte), pasa por un `GainNode` en 0 para evitar eco, manda PCM Int16 por WebSocket. La gráfica es **canvas vanilla** (confirmado con el usuario, mismo patrón que `discoLights.js`), con el mismo degradado celeste/blanco/rosa del medidor estático como fondo, no decorativo.
- **Verificación**: `backend/tests/test_stream.py` (2 tests: flujo exitoso de `score_update`, rechazo de handshake inválido), suite completa de backend en 13/13. Validado además con un cliente Python real (`websockets`) contra el servidor corriendo de verdad por red: 3 `score_update` recibidos, score consistente para un tono estable de 180Hz. Frontend: build limpio (`npm run build`, 15 módulos), 15/15 tests de Vitest, dev server sirviendo todos los archivos nuevos con 200. **Sin probar todavía con micrófono real en navegador** (sin herramienta de navegador disponible en la sesión donde se construyó); pendiente que el usuario lo pruebe en `http://localhost:5173`.

Sigue pendiente, no resuelto por esta implementación: si el modelo alguna vez se exporta a ONNX/WASM para correr completo en el cliente (la exportación a ONNX ya está listada como "próxima funcionalidad" en el README, pensada originalmente para móvil), eso reabriría la conversación de mover también la extracción de features al navegador.

**Fase 2 (backend de inferencia): implementada y validada.**
- `backend/app/`: `config.py` (settings vía `pydantic-settings`), `schemas.py` (contrato de `POST /api/v1/analyze` de `docs/API.md`), `audio/decode.py` (decodifica el upload a un archivo temporal que se borra en el mismo request, ver `docs/ETHICS_PRIVACY.md`), `scoring/model_loader.py` (carga el modelo y valida el feature schema al arrancar, falla rápido si no coincide), `scoring/predictor.py` (score = `predict_proba` calibrado × 100), `scoring/feedback.py` (retroalimentación en lenguaje llano, incluye el contraste explícito tono-vs-resonancia que es el principio central del proyecto), `api/routes_analysis.py`, `api/routes_health.py` (`/health`, `/api/v1/model-info`), `main.py`.
- Corre sobre `models/crisantemo_v1.joblib`, el modelo exportado con datos sintéticos en Fase 1; no hace falta tocar el backend cuando se reemplace por un modelo entrenado con datos reales, solo el archivo `.joblib`.
- Se quitó `webrtcvad` de `backend/requirements.txt`: es para el VAD del modo streaming (Fase 4), Fase 2 no lo usa, y requiere un compilador C que no estaba disponible al desarrollar esto.
- Verificación: `shared/tests/test_features.py` (F0 sobre tonos sintéticos con `numpy.sin`, silencio y clips cortos lanzan `InsufficientVoiceError`) y `backend/tests/` (`TestClient` de FastAPI: score en rango, rechazo de archivo vacío y de silencio, `/health`, `/model-info`); 10/10 tests pasan. También se corrió el servidor real con `uvicorn` fuera de Docker y se probó `POST /api/v1/analyze` con un WAV real por curl.
- En esta máquina sí fue posible construir la imagen (`docker compose build backend`) y levantar el contenedor (`docker compose up backend`) de punta a punta por primera vez; el healthcheck reportó `healthy` y `POST /api/v1/analyze` dentro del contenedor devolvió exactamente el mismo resultado que la corrida local.

## Limitación de red del entorno de desarrollo

El entorno donde se está construyendo este proyecto solo tiene acceso a los registros de paquetes (pip, npm/PyPI). No hay acceso a Hugging Face, Mozilla Common Voice, ni a ningún registro de imágenes Docker (Docker Hub, ghcr.io, etc.), confirmado probando varios hosts. Esto significa que, dentro de este entorno:

- No se puede correr `01_download_dataset.py` de verdad.
- No se puede hacer `docker compose build`/`up` (falla al intentar descargar la imagen base `python:3.11-slim`).

La descarga del dataset real y el build/despliegue completo con Docker deben correrse en un entorno con internet completo (la máquina del usuario, un servidor, un runner de CI). El código está escrito para eso; aquí solo se valida la lógica de Python/JS de forma aislada (fuera de Docker) y la sintaxis de `docker-compose.yml`.
