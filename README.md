![Made with Python](https://forthebadge.com/images/badges/made-with-python.svg)
![Build with Love](http://ForTheBadge.com/images/badges/built-with-love.svg)

```ascii
 ██████╗██████╗ ██╗███████╗ █████╗ ███╗   ██╗████████╗███████╗███╗   ███╗ ██████╗
██╔════╝██╔══██╗██║██╔════╝██╔══██╗████╗  ██║╚══██╔══╝██╔════╝████╗ ████║██╔═══██╗
██║     ██████╔╝██║███████╗███████║██╔██╗ ██║   ██║   █████╗  ██╔████╔██║██║   ██║
██║     ██╔══██╗██║╚════██║██╔══██║██║╚██╗██║   ██║   ██╔══╝  ██║╚██╔╝██║██║   ██║
╚██████╗██║  ██║██║███████║██║  ██║██║ ╚████║   ██║   ███████╗██║ ╚═╝ ██║╚██████╔╝
 ╚═════╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝     ╚═╝ ╚═════╝
       by Hex (@RemiH06)          version 0.1
```

![Maintained](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)
![Hippocratic License](https://img.shields.io/badge/License-Hippocratic--3.0-lightgrey.svg?style=for-the-badge)

## 🌼

### Descripción general

Crisantemo es una herramienta de análisis de voz pensada para acompañar a personas trans en general (sobre todo mujeres) en la práctica de su voz. A partir de una grabación o de audio en vivo, calcula una puntuación de 0 (percepción masculina) a 100 (percepción femenina), construida sobre features acústicas interpretables (tono, formantes, jitter, shimmer, relación armónico-ruido), no solo sobre el pitch. La razón de fondo es que la percepción de género en una voz depende sobre todo de la resonancia del tracto vocal, no del tono por sí solo: una voz aguda puede seguir sonando masculina, y una voz algo grave con buena resonancia puede sonar femenina. El proyecto está construido con esa distinción como principio de diseño, no como detalle técnico secundario.

Es una herramienta hermana e independiente de QuetzBeats/QuetzBoard, pensada también como add-on para artistas trans dentro de ese ecosistema.

El nombre viene del crisantemo, la flor que florece más tarde que las demás, en otoño, cuando el resto del jardín ya se marchitó. Se le asocia culturalmente con la resiliencia y con florecer en el propio tiempo, no en el esperado por otros. Nos pareció una metáfora apropiada para el proceso de encontrar y desarrollar la propia voz.

```diff
- Proyecto en desarrollo temprano (Fase 0 completada). Todavía no hay modelo entrenado ni build de Docker probado de punta a punta.
- La puntuación es una herramienta de práctica y retroalimentación, no un diagnóstico ni una medida de qué tan válida es una voz o una persona.
- El modelo se entrena sobre un dataset con etiquetas binarias de género (Mozilla Common Voice). Es una limitación técnica reconocida del estado actual de los datos abiertos disponibles, no una postura del proyecto sobre el género de nadie.
- Por defecto no se guardan grabaciones de audio del usuario; el procesamiento ocurre en memoria.
```

## Estructura del proyecto

- `backend/`: API FastAPI. Análisis de grabaciones completas (REST) y modo en vivo (WebSocket).
- `frontend/`: interfaz web (Vite + JS vanilla).
- `training/`: pipeline offline para entrenar el modelo a partir de Mozilla Common Voice. No es un servicio persistente, se corre bajo demanda.
- `shared/acoustic_features/`: extracción de features acústicas. La usan tanto `training` como `backend`, para que el modelo y el servicio de inferencia nunca queden desalineados.
- `models/`: artefactos del modelo entrenado (`.joblib` + `feature_schema_v1.json`, el contrato de columnas entre entrenamiento e inferencia).

## Puertos

| Servicio | URL local |
|---|---|
| frontend | http://localhost:9000 |
| backend (API + WebSocket) | http://localhost:9001 |
| training (opcional, bajo demanda) | http://localhost:9002 |

## Instalación

1. Copia el archivo de variables de entorno:

   `cp .env.example .env`

2. Levanta los servicios persistentes (frontend + backend):

   `docker compose up --build`

3. El pipeline de entrenamiento no se levanta con el comando anterior; se corre bajo demanda con el perfil `training`:

   ```bash
   docker compose --profile training run --rm training python scripts/01_download_dataset.py
   docker compose --profile training run --rm training python scripts/02_prepare_labels.py
   docker compose --profile training run --rm training python scripts/03_extract_features.py
   docker compose --profile training run --rm training python scripts/04_train_model.py
   docker compose --profile training run --rm training python scripts/05_evaluate_model.py
   docker compose --profile training run --rm training python scripts/06_export_model.py
   ```

## Configuración y variables de entorno

- `MODEL_PATH`: ruta al modelo serializado que carga el backend (por defecto `/app/models/crisantemo_v1.joblib`).
- `FEATURE_SCHEMA_PATH`: ruta al contrato de columnas del modelo (`feature_schema_v1.json`).
- `CORS_ORIGINS`: orígenes permitidos para el backend, separados por coma.
- `VITE_API_BASE_URL` / `VITE_WS_BASE_URL`: a dónde apunta el frontend para hablar con el backend (REST y WebSocket).
- Perfil `training` de docker compose: aísla el pipeline de entrenamiento de los servicios persistentes, para que nunca se levante junto a ellos por accidente.

## Funcionalidades

- Extracción de features acústicas (tono, formantes, jitter, shimmer, HNR) compartida entre entrenamiento e inferencia (fase 0, lista)
- Análisis de grabaciones completas vía API REST, con desglose de features y retroalimentación en lenguaje llano (fase 2)
- Interfaz web para grabar o subir audio y ver la puntuación (fase 3)
- Modo en vivo por WebSocket, con puntuación suavizada mientras se habla (fase 4)
- Indicador de calidad del audio de entrada (nivel, saturación, duración de voz detectada) (fase 4-5)

## Próximas funcionalidades

- Logo de Crisantemo (todavía no existe, la app usa solo texto)
- Exportación del modelo a ONNX para reutilizarlo desde una app móvil
- Historial de progreso por sesión de práctica
- Soporte multi-idioma en la extracción de entonación

## Licencia

Crisantemo usa la [Hippocratic License 3.0](https://firstdonoharm.dev/) (módulo core), no MIT. Es software libre en el sentido práctico (uso, copia, modificación y distribución, incluida comercial, sin costo), con una condición adicional: el uso debe respetar los derechos humanos reconocidos en la Declaración Universal de Derechos Humanos de la ONU, incluyendo la no discriminación por sexo, género y orientación sexual. Ver `LICENSE` para el texto completo.

## Documentación

- `docs/ARCHITECTURE.md`: decisiones de arquitectura y estado del proyecto por fase.
- `docs/TRAINING_REPRODUCTION.md`: cómo reproducir el pipeline de entrenamiento paso a paso, con o sin Common Voice.
- `docs/ETHICS_PRIVACY.md`: privacidad de los datos de voz, límites del dataset de entrenamiento y riesgos de mal uso.
- `docs/API.md`: diseño planeado de la API (REST y WebSocket), pendiente de implementarse en Fase 2.
