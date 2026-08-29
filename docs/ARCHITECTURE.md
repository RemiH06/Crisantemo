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

Razón de fondo, ya cuantificada con datos (ver `training/notebooks/feature_analysis.ipynb`): en este dataset, F0 por sí solo tiene AUC 0.97 clasificando género (casi perfecto), mientras que los formantes por sí solos tienen AUC 0.57-0.73 (apenas mejor que azar). No es que tono y resonancia vayan fuertemente correlacionados (la correlación real es débil, r=0.10-0.37); es que los formantes, calculados como promedio simple sobre toda la grabación, casi no separan las clases por sí solos en este dataset. Además, las grabaciones de tono agudo actuado están literalmente fuera del rango de F0 que el modelo vio en entrenamiento (casi no pasa de 300 Hz), así que ahí el modelo extrapola, no elige ignorar los formantes. Common Voice es voz leída de forma natural, no voz practicada/actuada deliberadamente (que es exactamente el caso de uso de Crisantemo), y ningún volumen adicional de Common Voice va a representar bien ese escenario extremo. El modelo actual (`models/crisantemo_v1.joblib`) se dejó como el de 5,000 reales + sintéticos decorrelacionados (mejor accuracy general, y el chequeo de estrés adversarial ya vive permanentemente en `05_evaluate_model.py`), sabiendo que este caso específico sigue sin resolverse. Caminos identificados para retomar: ampliar la generación sintética a un muestreo continuo (no solo 4 combinaciones fijas), conseguir datos reales de voz practicada/actuada, o considerar una arquitectura híbrida que le garantice un piso de peso a las features de resonancia en vez de dejarlo 100% aprendido.

## Fase 4 (modo en vivo): decisión de arquitectura

Para el modo en vivo se descartó Phoenix/Elixir (resolvería un problema de concurrencia masiva que este proyecto no tiene, y de todas formas necesitaría llamar a un servicio Python aparte porque parselmouth/librosa no existen en Elixir).

Decisión tomada (todavía sin implementar, Fase 4 no ha empezado): explorar compilar la extracción de features de `shared/acoustic_features` a WASM con Rust, para correrla directo en el navegador en vez de mandar el audio crudo al backend por WebSocket. Esto tiene dos beneficios concretos:

- **Privacidad**: el audio nunca sale del navegador, solo se transmite el vector de features (números pequeños), no la voz. Esto refuerza el principio de "no persistir/exponer audio" de `docs/ETHICS_PRIVACY.md`.
- **Resuelve de raíz la pregunta de cómo graficar en vivo**: si el cliente ya calcula las features localmente, la gráfica de pitch/formantes en vivo es un loop de animación sobre datos que el propio navegador produjo, sin esperar la ida y vuelta al servidor.

El costo real, y la razón de no hacerlo todavía: parselmouth envuelve Praat (C), no hay un puerto directo a Rust. Habría que reimplementar los algoritmos de F0 (autocorrelación o YIN) y de formantes (LPC) desde cero en Rust, y validar que esa segunda implementación produce los mismos números que `shared/acoustic_features` en Python, para no romper el contrato de que training e inferencia nunca diverjan (`models/feature_schema_v1.json`). Es una pieza de ingeniería real, no una tarde de trabajo.

Sigue pendiente, y hay que confirmarlo cuando se llegue a Fase 4: si el backend también recibe el vector de features (para correr el modelo ahí) o si el modelo también se exporta a ONNX/WASM y corre completo en el cliente (la exportación a ONNX ya está listada como "próxima funcionalidad" en el README, pensada originalmente para móvil, pero serviría igual aquí). Y, independiente de dónde corra el cómputo, sigue sin resolverse si la gráfica se dibuja con canvas vanilla o con una librería/framework como React; la recomendación fue vanilla+canvas salvo que el resto del proyecto vaya a crecer con mucha interfaz interactiva.

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
