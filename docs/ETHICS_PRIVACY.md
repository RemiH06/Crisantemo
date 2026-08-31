# Ética y privacidad

Este documento estaba contemplado en el plan original del proyecto (`docs/PLAN.md`) pero nunca se había escrito. Cubre tres cosas: qué pasa con el audio de quien usa Crisantemo, qué limitaciones tiene el dataset con el que se entrena el modelo, y qué riesgos de mal uso tiene una herramienta de este tipo.

## Qué es Crisantemo y qué no es

La puntuación de 0 a 100 es una herramienta de práctica y retroalimentación, no un diagnóstico ni una medida de qué tan válida es una voz o una persona. El modelo no mide identidad de género, mide percepción acústica promedio sobre un vector de features (tono, formantes, jitter, shimmer, HNR). Ninguna persona necesita "aprobar" un umbral de este modelo para que su identidad sea válida.

## Manejo del audio

Por defecto, Crisantemo no guarda grabaciones de audio de quien lo usa. El procesamiento ocurre en memoria: el backend recibe el audio, extrae features, calcula el score, responde, y no persiste el audio a disco ni a base de datos.

Esto es principalmente una decisión de privacidad, no de rendimiento. La voz es un dato biométrico y, en el caso específico de esta herramienta, un dato que además revela que quien la usa está practicando su voz, algo que muchas personas trans no quieren que quede registrado en ningún lado. No guardar el audio es lo que minimiza esa exposición: no hay una base de datos de grabaciones de voz de personas trans que pueda filtrarse, subpoenarse o reutilizarse sin consentimiento. El beneficio de rendimiento (no escribir a disco) es real pero secundario, no es la razón de fondo.

**Ya verificado en código, no solo prometido**: `backend/tests/test_privacy.py` confirma que el único lugar del backend que toca disco (`app/audio/decode.py`, un archivo temporal que `ffmpeg`/`audioread` necesitan para decodificar formatos comprimidos) siempre se borra antes de que la respuesta salga, incluso cuando el análisis se rechaza después (voz insuficiente, registro de tono inestable) o el archivo es inválido. `grep` confirma que ningún otro archivo del backend escribe a disco. Sigue habiendo un límite honesto: no hay una prueba automática de que nada se filtre a logs (uvicorn no registra el cuerpo del request por default, pero eso es comportamiento por defecto de la librería, no algo que este proyecto configuró explícitamente ni probó).

Cuando se construya la funcionalidad de "historial de progreso por sesión" (mencionada en README como próxima funcionalidad), el mismo principio aplica: lo que se guarda debe ser el score y el desglose de features de esa sesión, no el audio en sí. Si en algún momento se quiere ofrecer guardar el audio (por ejemplo, para que la persona pueda reescuchar su propia grabación), debe ser opt-in explícito por sesión, nunca comportamiento por defecto.

## Limitaciones del dataset de entrenamiento

El modelo se entrena sobre Mozilla Common Voice, que etiqueta a quien dona voz con un campo binario de género. Esto es una limitación técnica reconocida del estado actual de los datos abiertos disponibles, no una postura del proyecto sobre el género de nadie. En concreto:

- Las etiquetas reflejan cómo se autodescribió cada persona que donó su voz al dataset, no una taxonomía impuesta por el proyecto.
- Un dataset binario no puede, por construcción, representar la diversidad real de voces trans, no binarias o de género fluido. El score de 0 a 100 es un espectro de percepción acústica, no una afirmación sobre cuántas categorías de género existen.
- El criterio de aceptación del modelo (`training/scripts/05_evaluate_model.py`, peso de F0 no debe dominar la decisión) existe en parte para reducir el riesgo de que el modelo aprenda un atajo simplista (solo pitch) en vez de la señal real (resonancia), que es más representativa de cómo se percibe una voz en la práctica.

El modelo actual (`models/crisantemo_v1.joblib`) se entrenó con dos datasets de [Mozilla Data Collective](https://mozilladatacollective.com) curados por "MDC Curators": subsets de Common Voice 26.0 en español mexicano, filtrados a audio ya validado por la comunidad (mínimo un upvote, cero downvotes) y separados por género autorreportado, bajo licencia CC0-1.0. Los términos de uso de esos datasets piden explícitamente no intentar identificar a las personas que grabaron los clips y no redistribuir el dataset; este proyecto respeta ambas cosas: `training/data/raw/` (el audio en sí) está en `.gitignore` y nunca se sube al repo, y lo que sí se versiona (`training/data/processed/`, con features acústicas ya extraídas) no incluye audio ni identificadores de las personas que hablan, solo mediciones numéricas por clip.

**Limitación importante y sin resolver todavía:** Common Voice es voz leída de forma natural por voluntarios, nadie ahí está practicando deliberadamente cambiar su registro de voz. El caso de uso real de Crisantemo (alguien practicando separar tono de resonancia a propósito) casi no tiene representación en ese tipo de dataset, sin importar cuánto volumen se le meta; se confirmó esto probando con voz actuada real, donde el modelo se sigue dejando engañar por el tono en casos concretos (detalle técnico completo en `docs/TRAINING_REPRODUCTION.md` secciones 4.3-4.9 y `docs/ARCHITECTURE.md`). Esto es relevante aquí, en el documento de ética, y no solo en los documentos técnicos, porque es exactamente el tipo de usuario al que Crisantemo dice servir (alguien practicando su voz) el que más puede toparse con esta limitación. **Ya se comunica en la interfaz** (callout "Antes de empezar" en `frontend/src/app.js`, pantalla inicial), no solo queda documentado internamente; falta seguir mejorando el modelo en sí.

## Riesgo de mal uso

Un clasificador de percepción de género a partir de voz es una tecnología de doble uso. La misma extracción de features y el mismo modelo que ayudan a alguien a practicar su voz podrían, en teoría, reutilizarse para perfilar o intentar identificar voces trans con fines hostiles (por ejemplo, como parte de un sistema de detección o discriminación). Esto no es un riesgo hipotético lejano, es inherente a qué hace el modelo.

Cómo responde el proyecto a esto, hasta ahora:

- **Licencia**: Crisantemo usa la Hippocratic License 3.0 en vez de una licencia permisiva sin condiciones (ver `LICENSE`), que prohíbe explícitamente el uso del software para violar derechos humanos, incluyendo discriminación por género y orientación sexual.
- **Alcance del producto**: el proyecto no incluye, y no debe incluir sin discutirlo explícitamente antes, funcionalidades de identificación de hablantes (speaker identification/voiceprinting) ni de vinculación de un score con una identidad persistente más allá de una sesión de práctica local. Añadir algo así cambiaría el perfil de riesgo del proyecto y debe tratarse como una decisión de arquitectura mayor, no como una feature más.
- **Transparencia del dataset**: la limitación de las etiquetas binarias de Common Voice se documenta abiertamente (ver arriba) para no dar una falsa impresión de objetividad o precisión del modelo.

Esta sección debe revisarse cada vez que se agregue una funcionalidad nueva que toque identidad, almacenamiento de audio, o exportación de datos (por ejemplo, la app móvil o el historial de progreso mencionados en "próximas funcionalidades" del README).
