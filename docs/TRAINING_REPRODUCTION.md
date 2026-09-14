# Cómo reproducir el pipeline de entrenamiento y el reporte de evaluación

Esto documenta exactamente los pasos que se corrieron para llegar a `training/data/reports/eval_v1.md`. Sirve tanto para repetirlo con el dataset sintético de prueba como, en una máquina con internet completo, para correrlo con Mozilla Common Voice de verdad.

**Estado actual (fin de la investigación de sesgo de tono, por ahora): `models/crisantemo_v1.joblib` es 5,000 clips reales + 3,000 sintéticos decorrelacionados con formantes variables, entrenado con `--adversarial-weight 5` y calibrado con `FrozenEstimator` sobre el split de val** (secciones 2A, 2C, 4.6-4.9). De 5 grabaciones reales de prueba, una ya cruza correctamente a masculino tras forzar tono agudo sin trabajar resonancia; las otras mejoraron pero no todas cruzaron del todo. Mejora real, no una solución completa. Historia completa con números en las secciones 4.3 a 4.9, que es justo donde continuar.

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

## 2C. Mezclar con ejemplos sintéticos decorrelacionados (recomendado, ver sección 4.3/4.4)

Después de encontrar que el modelo entrenado solo con voz real usa el tono como atajo (sección 4.3), se agregó un generador de ejemplos sintéticos donde tono y formantes varían de forma **independiente** (a diferencia de `_dev_synthetic_dataset.py`, donde siguen yendo de la mano), etiquetados estrictamente por los formantes. Mezclarlos con los datos reales fuerza al modelo a no depender solo del tono.

```bash
cd training
python scripts/_dev_synthetic_decorrelated.py --n-per-combo 200

# Pega las filas sintéticas al final del manifest real (sin repetir el header)
tail -n +2 data/raw/manifest_synthetic_decorrelated.csv >> data/raw/manifest_es-mx.csv

python scripts/02_prepare_labels.py --lang es-mx
```

`02_prepare_labels.py` no necesita cambios: balancea y separa train/val/test sobre lo que haya en el manifest, sin distinguir origen real vs. sintético. Como se agrega la misma cantidad a cada género (2 de las 4 combinaciones son "femenino", 2 son "masculino"), el balance de clases no se distorsiona.

`05_evaluate_model.py` detecta automáticamente las filas sintéticas decorrelacionadas en el test set (por el nombre del archivo) y reporta accuracy por separado sobre los casos "adversariales" (tono y formantes en direcciones opuestas), no solo la importancia global de F0. Es la prueba de estrés real del principio central del proyecto, corriendo en cada evaluación, no un script manual aparte.

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

## 4.3. Hallazgo con el modelo de 500 clips: sobrepeso de F0 en casos actuados

Con el modelo entrenado sobre 500 clips reales (ver sección 2A), se probó manualmente con dos grabaciones de la misma persona, ambas voz actuada sin práctica previa (una aguda, una grave, sin esfuerzo de trabajar resonancia):

| | Aguda (score 94.6) | Grave (score 5.8) |
|---|---|---|
| F0 | 321 Hz | 125 Hz |
| F2-F1 (espaciado) | 666 Hz | **985 Hz** |
| F3 | 2060 Hz | **2592 Hz** |
| Brillo espectral | 794 Hz | **1106 Hz** |

La grabación grave tiene formantes objetivamente más "grandes" (más asociados a resonancia percibida como femenina) que la aguda, y aun así puntuó mucho más bajo. Esto contradice el principio central del proyecto para este caso puntual, aunque el peso global de F0 reportado por `05_evaluate_model.py` (33.7%) esté debajo del umbral de advertencia (60%): un promedio global sobre el test set no garantiza el comportamiento en casos fuera de lo típico del dataset (voz actuada deliberadamente en falsete/pecho, poco representada en solo 350 ejemplos de entrenamiento).

Esto motivó reentrenar con más datos (sección 2A, `--max-rows` más alto). Si el problema persiste con más datos, valdría la pena revisar si LightGBM (que ganó por poco sobre logreg en la comparación de `04_train_model.py`) está sobreajustando a F0 en datasets chicos, o si hace falta penalizar explícitamente las features de F0 en el entrenamiento.

## 4.4. Más datos reales no lo arregló; datos sintéticos decorrelacionados tampoco (para este caso)

Se probaron tres modelos contra las dos grabaciones reales exactas de la sección 4.3 (mismos 12 valores de features, sin volver a grabar):

| Modelo | Aguda | Grave |
|---|---|---|
| 500 clips reales | 94.6 | 5.9 |
| 5,000 clips reales (10x más datos, sin cambios de metodología) | 99.2 | 2.0 |
| 5,000 reales + 800 sintéticos decorrelacionados (`_dev_synthetic_decorrelated.py`, sección 2C) | 99.7 | 2.0 |

**Más datos reales empeoró el problema, no lo arregló.** La hipótesis: en voz real, tono y resonancia van correlacionados de forma natural (quien tiene voz más aguda de forma natural también suele tener un tracto vocal más corto). Meterle más voz real solo le dio al modelo más evidencia de esa correlación, reforzando el atajo "tono alto = femenino" en vez de debilitarlo.

**Mezclar datos sintéticos decorrelacionados tampoco lo arregló**, a pesar de llegar a 100% de accuracy en la prueba de estrés automática sobre esos mismos ejemplos sintéticos (ver el chequeo nuevo en `05_evaluate_model.py`). El modelo aprendió a resistir el atajo *dentro de las 4 combinaciones sintéticas exactas* que se le enseñaron, pero eso no generalizó a la grabación real, cuyos valores de features caen en un punto del espacio que no se parece lo suficiente a ninguna de esas 4 esquinas fijas (perfil de formantes "masculino" o "femenino" × rango de tono "grave" o "agudo").

Hay algo más de fondo que vale la pena decir con claridad: **Common Voice es voz leída de forma natural por voluntarios, nadie ahí está practicando cambiar su registro de voz a propósito.** El caso de uso real de Crisantemo (alguien practicando deliberadamente separar tono de resonancia, con distintos niveles de habilidad/práctica) casi no tiene representación en ningún dataset de voz leída, sin importar cuánto volumen se le meta. Es un límite de fondo del tipo de dataset, no solo de tamaño.

Caminos identificados para seguir desde aquí (sin explorar todavía, quedan como siguiente sesión):

1. **Ampliar la generación sintética decorrelacionada** de 4 combinaciones fijas a un muestreo continuo e independiente de tono y formantes en rangos amplios, para cubrir mejor el espacio real de features en vez de solo 4 esquinas exactas.
2. **Conseguir datos de voz practicada/actuada de verdad**, no solo lectura natural. Ninguna cantidad de Common Voice va a tener esto; haría falta una fuente de datos distinta (o generar activamente ejemplos con voluntarios, con todo el cuidado ético que implica pedirle a alguien que grabe su voz para este propósito específico, ver docs/ETHICS_PRIVACY.md).
3. Revisar si vale la pena una arquitectura híbrida: que el score no dependa 100% de un modelo de caja negra, sino que le dé un piso/techo garantizado a las features de resonancia sobre el tono (una regla explícita, no aprendida).

## 4.5. Por qué, en realidad: F0 casi separa solo, los formantes por sí solos casi no

`training/notebooks/feature_analysis.ipynb` (análisis exploratorio sobre las 5,000 filas reales) da la respuesta cuantitativa a por qué pasa esto, y corrige la hipótesis de la sección 4.4:

- **F0 por sí solo tiene AUC 0.97** clasificando género en este dataset (casi perfecto). **Los formantes por sí solos tienen AUC 0.57-0.73** (apenas mejor que azar en algunos casos). Las distribuciones de F1/F2/F3/F2-F1/F3-F2 por género se traslapan muchísimo; la de F0 casi no se traslapa.
- La correlación entre F0 y los formantes es en realidad **débil** (r=0.10 a 0.37, no la "correlación natural fuerte" que se asumió en la sección 4.4). El problema no es que tono y resonancia vayan de la mano en los datos: es que los formantes, calculados como promedio simple sobre toda la grabación, casi no separan las clases por sí solos en este dataset. El modelo no "prefiere" el atajo del tono por pereza, es la señal objetivamente más fuerte disponible.
- Las grabaciones de tono agudo actuado (320-356 Hz) están **fuera del rango de F0 que el modelo vio en entrenamiento** (que casi no pasa de 300 Hz). No es que el modelo ignore los formantes ahí: está extrapolando a una zona de tono nunca vista, y lo único que sabe hacer con tonos muy altos es "más femenino". Esto también explica por qué mezclar sintéticos decorrelacionados (sección 4.4) no ayudó: sus rangos de F0 (85-140 y 170-260) tampoco cubren esa zona extrema.

Ver el notebook para las gráficas completas (distribución por feature, matriz de correlación, AUC univariado, y dónde caen los 5 casos de prueba reales sobre la nube de entrenamiento) y las conclusiones con los próximos pasos concretos identificados.

**Decisión tomada por ahora:** se dejó el modelo de 5,000 reales + sintéticos decorrelacionados como `models/crisantemo_v1.joblib` (mejor accuracy general, 97.47%, y el chequeo automático de estrés adversarial ya vive en `05_evaluate_model.py` para cualquier reentrenamiento futuro), sabiendo que el caso específico de voz actuada con tono forzado sigue sin resolverse. No se revirtió a un modelo anterior porque ninguno de los tres resuelve el problema real; se prefirió quedarse con el de mejor accuracy general mientras se decide la estrategia de fondo.

## 4.6. Normalizar amplitud: probado, sin efecto (y por qué)

Se agregó `normalize_amplitude()` a `shared/acoustic_features/io.py` (normaliza a un RMS de referencia, ver el código) por si el volumen de grabación estaba metiendo ruido a features como HNR/shimmer. Se reentrenó con esto activo: **resultado byte-idéntico al anterior**, ninguna métrica cambió. Tiene una explicación limpia: las 12 features del vector ya son matemáticamente invariantes a la amplitud (HNR/jitter/shimmer son razones o porcentajes, F0/formantes/brillo espectral son frecuencias, ninguna es una medida de nivel/volumen crudo). El código se dejó (no hace daño, es buena práctica), pero confirmó que esta no era la pieza que faltaba. Tiene tests en `shared/tests/test_io.py`.

## 4.7. Por qué la aumentación sintética no transfería a voz real (encontrado y arreglado)

Con la mezcla de sintéticos decorrelacionados de la sección 2C/4.4, el modelo llegaba a 100% en la prueba de estrés *sintética* pero seguía fallando igual de mal en las grabaciones reales de la sección 4.3. Se investigaron y arreglaron tres causas, en orden de qué tanto importaron:

1. **Los formantes sintéticos eran 2 valores FIJOS exactos** (730/1090/2440 y 850/1650/2950), repetidos miles de veces, y ni siquiera caían en el rango real (el F1 real masculino promedia 456Hz, no 730). Un modelo de árboles puede aprender a reconocer esos números exactos como "esto es sintético, aquí sí uso formantes" en vez de aprender el patrón real de resonancia, que no ayuda en nada con una grabación real donde los formantes nunca son exactamente 730.000. **Este fue el cambio que finalmente movió la aguja** (ver 4.8). Se cambió a muestrear F1/F2/F3 de una distribución normal por género, calibrada con la media/desviación real de los propios datos de entrenamiento (`FORMANT_STATS` en `_dev_synthetic_decorrelated.py`).
2. Las voces sintéticas tenían jitter/shimmer/HNR sospechosamente "limpios" comparado con voz real (shimmer sintético 4.0% vs real 11.0%, HNR sintético 15.8dB vs real 13.0dB): otra señal fácil de "esto es sintético". Se recalibraron los parámetros de ruido de `synth_vowel()` en `_dev_synthetic_dataset.py` (`jitter_std`, `shimmer_std`, `noise_std`, ahora aleatorios por clip) para que caigan dentro del rango real.
3. Las voces sintéticas eran un tono sostenido parejo (sin entonación), mientras que voz real tiene el tono subiendo y bajando a lo largo de una oración: F0_std sintético 14Hz vs real 33Hz. Se agregó un contorno de entonación (`intonation_semitone_std`, un paseo aleatorio suavizado en semitonos) a `synth_vowel()`.

Los cambios 2 y 3, solos, **no movieron nada** en las grabaciones reales de prueba (se probó cada uno por separado, con reentrenamientos completos entre cada uno). Solo cuando se combinaron con el cambio 1 (formantes variables) hubo una mejora real. Esto sugiere que el "atajo de detectar sintético" más fuerte de los tres era, por mucho, el de los formantes fijos, no los otros dos ruidos (aunque vale la pena mantenerlos, son gratis y hacen la síntesis más honesta de todas formas).

## 4.8. Resultado con formantes variables: mejora real, pero parcial

Con las tres correcciones de la sección 4.7 juntas, comparando el mismo conjunto de grabaciones reales de prueba contra el modelo (usando los 12 valores de features exactos que se reportaron en cada caso, no reanálisis de audio):

| Caso | Antes de todo esto | Con formantes variables |
|---|---|---|
| Aguda actuada | 94.6 | **71.0** |
| Aguda actuada nueva | 92.8 | **58.6** |
| Grave actuada | 5.9 | 2.6 |
| Voz normal | 0.3 | 0.6 |
| Voz más grave | 2.3 | 2.2 |

Las voces masculinas se quedaron igual de bien clasificadas. Las dos voces agudas actuadas bajaron mucho de "casi seguro femenino" a "ambiguo, apenas del lado femenino" (58.6 está prácticamente en la frontera de "andrógeno" según las bandas de `feedback.py`). **No se arregló del todo** (no se voltearon a masculino), pero es la primera mejora real medible en toda la investigación, no solo en datos sintéticos.

El costo: accuracy general bajó de 98% a **85.15%**, y la prueba de estrés sintética bajó de 100% a **61.6%** (por debajo del umbral de advertencia de 70% en `05_evaluate_model.py`, que ahora sí avisa correctamente). Interpretación: con formantes fijos el modelo podía memorizar 2 valores exactos y sacar 100% "haciendo trampa"; con formantes variables ya no puede memorizar, tiene que generalizar de verdad, y le cuesta trabajo genuino (61.6%, por arriba de azar pero lejos de perfecto).

**Confirmación en producción, no solo con números pegados:** se probó una grabación real nueva (voz actuada, descrita como "se oye muy fingida" al reescucharla con el reproductor del frontend) contra el modelo ya desplegado, y dio 97%. Confirma que la mejora es real pero parcial: sigue fallando en voz claramente forzada/actuada.

**Para retomar mañana:**
- Si se comparte el desglose completo de esa grabación nueva (con el reproductor + "ver las 12 features completas" del frontend), agregarla a la lista de casos de prueba conocidos.
- Caminos no explorados todavía: más ejemplos sintéticos con formantes variables (ahora mismo son 3,000, mismos que con formantes fijos), variar la severidad de shimmer/jitter/entonación de forma correlacionada con el género (en voz real también difieren un poco por género, no solo por individuo), o pesar más los combos adversariales específicamente en vez de repartir parejo entre los 6 combos.
- Sigue sin intentarse: pitch-normalizar antes de medir formantes (la idea original de esta sesión, pausada por la investigación de por qué la aumentación sintética no transfería) y el estimado de longitud de tracto vocal a partir de dispersión de formantes.

## 4.9. Pesar los casos adversariales: mejora real (con dos bugs encontrados en el camino)

Siguiente experimento, barato porque no necesita re-extraer features: en `04_train_model.py`, entrenar el modelo final dándole más peso (`sample_weight`, `--adversarial-weight`, default 5x) a los 500 ejemplos de cada combinación adversarial (tono agudo + formantes masculinos, tono grave + formantes femeninos) contra el resto. La comparación de CV entre logreg/LightGBM se queda sin peso (es solo para elegir el algoritmo).

Al probar contra las 5 grabaciones reales, los números salieron **idénticos** a la corrida anterior sin peso. Investigando por qué, se encontraron dos bugs reales en `06_export_model.py`:

1. **El peso nunca llegaba al modelo exportado.** `CalibratedClassifierCV(raw_model, cv=5).fit(X_train, y_train)` clona y REENTRENA `raw_model` desde cero en cada uno de los 5 folds, sin pasarle `sample_weight`. El modelo entrenado con peso (`crisantemo_v1_raw.joblib`) sí lo tenía, pero se descartaba silenciosamente al calibrar. Se corrigió pasando `sample_weight` también aquí.
2. **Aun corregido, calibrar con `cv=5` seguía dando peor resultado que el modelo crudo sin calibrar.** Reentrenar 5 copias, cada una con 4/5 de los datos, diluye el efecto del peso. La solución (que además ya estaba anotada como pendiente en el código desde antes de esta sesión: "una vez que haya volumen de datos real, vale la pena calibrar sobre el split de val con cv='prefit'") es calibrar sin reentrenar: usar `raw_model` tal cual (ya con su peso adentro) y solo ajustar la curva de calibración sobre el split de validación, datos que el modelo no vio en entrenamiento. `cv="prefit"` está removido en scikit-learn >= 1.6 (este proyecto usa 1.9); el reemplazo es envolver el modelo con `sklearn.frozen.FrozenEstimator`.

Con ambos bugs corregidos, comparado contra las 5 grabaciones reales:

| Caso | Al empezar la sesión | Con formantes variables (4.8) | Con peso adversarial + calibración corregida |
|---|---|---|---|
| Aguda actuada | 94.6 | 71.0 | 74.4 |
| Aguda actuada nueva | 92.8 | 58.6 | **33.7 (cruzó a masculino)** |
| Grave actuada | 5.9 | 2.6 | 11.5 |
| Voz normal | 0.3 | 0.6 | 2.9 |
| Voz más grave | 2.3 | 2.2 | 4.0 |

**"Aguda actuada nueva" cruzó al lado masculino por primera vez en toda la investigación.** Las tres voces masculinas se mantienen correctamente clasificadas, con algo más de margen que antes pero sin cruzar. "Aguda actuada" (la primera, F0 más bajo que la nueva pero aun así el caso más extremo del set) sigue sin cruzar. Mejora real y medible, todavía no una solución completa.

## 4.10. Subir el peso adversarial de 5x a 10x: mejora clara en la prueba automática, pero con un riesgo nuevo encontrado

Siguiente experimento, barato porque no necesita re-extraer features: barrer `--adversarial-weight` de 5 a 20 y comparar contra `05_evaluate_model.py` (accuracy general de test + accuracy en los 242 casos adversariales sintéticos del split de test).

| Peso | Accuracy general (test) | Accuracy en adversariales sintéticos | Peso combinado de F0 |
|---|---|---|---|
| 5 (anterior) | 81.7% | 85.5% | 31.3% |
| 8 | 80.0% | 88.8% | 31.5% |
| 10 | 79.5% | 91.7% | 30.1% |
| 15 | 77.4% | 92.1% | 29.0% |
| 20 | 76.3% | 93.8% | 27.8% |

Tendencia clara y monótona: más peso adversarial mejora la robustez a casos donde tono y formantes van en direcciones opuestas, a costa de accuracy general. El usuario eligió 10 (mejor relación ganancia/costo, los pesos de 15 y 20 ya son retornos decrecientes). Modelo reentrenado, recalibrado (mismo procedimiento `FrozenEstimator` de 4.9) y exportado a `models/crisantemo_v1.joblib`.

**Riesgo nuevo encontrado al verificar con la prueba de estrés manual de la sección 5** (4 voces sintéticas de control, un solo trazo de ruido cada una): con la voz "grave + formantes masculinos" (f0=100Hz, formantes 730/1090/2440, un caso NO adversarial, pitch y formantes ya apuntan los dos a masculino) el score subió de forma monótona con el peso: 34.2 (peso 1) → 54.1 (peso 5) → 74.0 (peso 10), cruzando a "feminino" en vez de quedarse masculino. Investigando la causa: Praat/Burg mide mal F1 en esta síntesis específica (extrae 869Hz cuando el objetivo era 730Hz, probablemente porque a F0=100Hz los armónicos son tan espaciados que el 8vo/9no armónico, cerca de 800-900Hz, se confunde con el pico de F1), lo que colapsa `f2_f1_diff_hz` a 269.8 (más estrecho que cualquier caso femenino real del dataset). Subir el peso adversarial hace que el modelo dependa más de `f2_f1_diff_hz` específicamente, así que amplifica el efecto de este ruido de medición en vez de solo corregir los casos adversariales genuinos.

Con la misma prueba, el caso "agudo + formantes femeninos" (consistente, debería ser confiablemente femenino) tampoco se clasifica con confianza en ningún peso (54.6 / 42.8 / 53.9): sugiere que la prueba de estrés manual de la sección 5, tal como está escrita hoy (un solo trazo de síntesis por caso, con un `rng` compartido y mutado secuencialmente entre casos, sin repetir con más semillas), es ruidosa por sí misma y no es una señal confiable para decidir esto sola. La prueba automática de `05_evaluate_model.py` (242 ejemplos, no 1) sigue siendo la señal más confiable de las dos, pero ninguna reemplaza probar con voz real.

**Implicación práctica:** el modelo exportado con peso 10 no se puede dar por bueno solo con la prueba automática. Falta que el usuario reconfirme en el frontend, con grabaciones reales: (a) si "aguda actuada" por fin cruza a masculino, y (b) que las voces masculinas ya confirmadas (voz normal, voz más grave, grave actuada) no se hayan movido hacia femenino por este mismo efecto. Si (b) falla, es evidencia de que este riesgo del formant-tracking a F0 bajo también aplica a voz real grave, no solo a la síntesis de prueba, y valdría la pena retomar la idea pausada de pitch-normalizar antes de medir formantes (ver cierre de la sección 4.8), que ataca la causa raíz en vez de compensarla con más peso.

## 4.11. Confirmado con voz real: peso 10 rompe casos fáciles, se revierte a 5

El riesgo de la sección 4.10 se confirmó, y peor de lo anotado ahí: el usuario probó el modelo con peso 10 en producción y lo describió como "no tiene ni pies ni cabeza, funciona mucho peor que el anterior". Un sanity check rápido con voces sintéticas de control (no adversariales, tono y formantes apuntando ambos a la misma dirección) confirmó el problema con números:

| Caso (sintético, no adversarial) | Peso 10 | Peso 5 (revertido) |
|---|---|---|
| Grave + formantes masculinos (debería ser claramente masculino) | **57.3** | 25.2 |
| Aguda + formantes femeninos (debería ser claramente femenino) | 72.4 | 75.4 |
| Femenina algo más grave | 50.9 | 48.6 |

Con peso 10, una voz masculina de manual (sin ninguna ambigüedad) puntuaba 57.3, prácticamente una moneda al aire, no solo el caso límite "aguda actuada" que se estaba intentando arreglar. La ganancia en la prueba de estrés adversarial (85.5%→91.7%) no valía ese costo: el modelo dejó de funcionar bien en los casos fáciles y comunes para mejorar marginalmente en los casos raros/extremos. Confirma en voz real lo que 4.10 ya sospechaba solo con síntesis de prueba: subir el peso adversarial hace al modelo depender más de `f2_f1_diff_hz`, y esa dependencia extra sale cara en casos normales, no solo en el edge case de F0 bajo con formant-tracking ruidoso.

**Se revirtió a `--adversarial-weight 5`** (el valor de la sección 4.9, ya validado con las 5 grabaciones reales). `models/crisantemo_v1.joblib` vuelve a ese estado. El pendiente de "aguda actuada" (el único de los 5 casos de prueba que nunca cruzó a masculino) sigue abierto, pero subir el peso adversarial a secas queda descartado como camino: ya se probó en dos direcciones (10 y hasta 20 en el barrido de 4.10) y el costo en casos fáciles es real, no hipotético. Caminos que siguen abiertos, sin este descartado: pitch-normalizar antes de medir formantes, o una arquitectura híbrida con piso de peso garantizado para features de resonancia (ambos ya anotados en el cierre de 4.8).

## 4.12. ¿Ayudaría agregar otros idiomas? Explorado con datos reales, respuesta: no es gratis

Pregunta del usuario: como las 12 features son acústicas (no dependen del idioma ni de qué se dijo), ¿serviría agregar Common Voice de otros países/idiomas para tener más datos reales? Se investigó con datos de verdad en vez de asumir: se descargaron 250 clips por género de inglés estadounidense, neerlandés y árabe (mismos datasets "MDC Curators" gender-curated que ya se usan para es-mx, ver `LANGUAGE_DATASETS` en `01_download_dataset.py`), y se comparó contra es-mx en `training/notebooks/feature_analysis.ipynb` sección 6.

**La dirección del efecto de género es la misma en los 4 idiomas, en las 12 features** (F0 más alto en femenino, jitter/shimmer más altos en masculino, HNR más alto en femenino, siempre). Confirma que el patrón es físico, no un artefacto del idioma. Pero **el tamaño de la brecha varía, y no a favor de la resonancia**: el espaciado F2-F1 separa géneros por ~66-84 Hz en es-mx/en-US/árabe, pero en neerlandés casi se invierte (masculino 1149.6 vs femenino 1133.5). El neerlandés también tiene el HNR más bajo de los 4 para ambos géneros a la vez (11.8/8.6 contra 14-15/9-11 en los demás), señal más probable de calidad de grabación del subset que de una diferencia real de habla regional, aunque con solo 250 clips por género no se puede afirmar con certeza.

**Conclusión práctica: agregar estos idiomas al entrenamiento real no es "más datos gratis mejor".** La señal de resonancia, ya débil de por sí (AUC 0.57-0.73 en es-mx, sección 3 del notebook), se ve todavía más débil o invertida en al menos uno de los 3 idiomas nuevos. Mezclarlos sin cuidado arriesga diluir más la señal de formantes que reforzarla. No se agregó nada al pipeline de entrenamiento (`02_prepare_labels.py`/`03_extract_features.py` no tocan estos datos, la comparación se hizo en memoria dentro del notebook); si se retoma este camino, lo primero sería descargar más de 250 clips por idioma para confirmar si el patrón de neerlandés es real o ruido de muestra chica.

## 4.13. "Aguda actuada" no cae en NINGÚN clúster: es un outlier en 3 ejes a la vez, no solo en F0

Pregunta del usuario, motivada por ver que en el scatter matrix (sección 5 del notebook) los géneros se separan de forma bastante homogénea: ¿el modelo podría puntuar según qué tan bien encaja una voz dentro de su clúster, en vez de solo clasificar? Se construyó una vista 3D (F0 x HNR x F3, color por shimmer con dos escalas distintas por género, sección 5.1 del notebook) con los 5 casos de prueba reales superpuestos, y se calculó el percentil exacto de cada caso contra cada clúster en esos 3 ejes:

| Caso | vs. femenino (F0 / HNR / F3) | vs. masculino (F0 / HNR / F3) |
|---|---|---|
| Aguda actuada | 100% / 100% / **0%** | 100% / 100% / **0%** |
| Aguda actuada nueva | 100% / 100% / **0%** | 100% / 100% / **0%** |
| Grave actuada | 0% / 4% / 15% | 28% / 26% / 41% |
| Voz normal | 0% / 6% / 2% | 11% / 39% / 5% |
| Voz más grave | 0% / 9% / 5% | 2% / 49% / 13% |

**Los dos casos "aguda actuada" no caen adentro de ningún clúster: son outliers extremos en los 3 ejes a la vez**, no solo en F0 como ya se sabía (sección 4.5/conclusiones del notebook). Están en el percentil más alto del dataset en F0 y en HNR, y al mismo tiempo en el percentil más bajo en F3, para cualquiera de los dos géneros. El modelo no tiene ninguna zona de entrenamiento cerca de ese punto; está extrapolando a ciegas, no ignorando la resonancia a propósito. Las tres voces masculinas bien clasificadas, en cambio, caen en percentiles moderados (26-49%) contra su clúster: son ejemplos típicos, no casos límite.

**Implicación:** esto es evidencia concreta a favor de complementar (no necesariamente reemplazar) el clasificador actual con una señal de "qué tan típica es esta voz de algo que el modelo ya vio" (ej. `QuadraticDiscriminantAnalysis` o una mezcla de gaussianas por género en sklearn, comparando verosimilitud contra ambos clústers en vez de solo la frontera de decisión de LightGBM). Un caso "aguda actuada" habría salido con baja confianza/alta atipicidad bajo ese enfoque, coincidiendo con que hoy el modelo simplemente no sabe qué hacer con él. No implementado todavía, queda como siguiente experimento candidato junto con pitch-normalizar formantes y la arquitectura híbrida (cierre de 4.8).

## 4.14. Confirmado con jitter/shimmer reales: forzar el tono limpia la fonación de verdad, no es un artefacto de grabación

La sección 4.13 solo tenía 6 de las 12 features para los casos de prueba (`known_cases` nunca capturó jitter/shimmer). El usuario grabó 5 pruebas nuevas con el desglose completo desde el frontend (modelo con peso 5): aguda actuada, grave actuada, y 3 grabaciones "regular" de control (mismo micrófono/cuarto, para aislar si el patrón es de grabación o de la voz). Percentil contra el dataset real de entrenamiento:

| Caso | F0 | Jitter | Shimmer | HNR |
|---|---|---|---|---|
| Aguda actuada (342 Hz) | 100% | **0%** | **0%** | 100% |
| Grave actuada (105 Hz) | 0-3% | 30-61% | 0-2% | 84-99% |
| Regular x3 (107-118 Hz) | 0-17% | 23-94% | 3-80% | 10-93% |

**"Aguda actuada" es un outlier cuádruple: F0 más alto que cualquier grabación de entrenamiento, y jitter/shimmer más bajos que absolutamente cualquiera, con HNR más alto que cualquiera.** Las 3 grabaciones "regular", mismo setup, caen en percentiles normales y dispersos (10-94%): descarta que sea el micrófono o el cuarto. Solo al forzar el tono a 342 Hz la fonación se vuelve anormalmente "limpia" en las 3 métricas de perturbación a la vez. Confirma con datos reales la hipótesis: es una firma fisiológica real de forzar el tono muy por fuera del registro cómodo (vibración de cuerdas vocales más simple/periódica), no ruido de medición ni de grabación.

Detalle adicional: esta vez F3 no salió extremo (percentil 27-62%, normal), a diferencia de los casos de 4.13 donde sí lo era. Jitter/shimmer/HNR parece ser la señal más consistente de "esto es tono forzado" entre sesiones de grabación distintas, más que F3. "Grave actuada" muestra una versión más chica del mismo patrón (shimmer bajo, HNR alto vs. las 3 "regular"), sugiriendo que cualquier actuación de voz limpia la fonación algo, y forzarla muy lejos del registro cómodo la limpia mucho.

**Siguiente experimento propuesto, no implementado todavía:** ampliar `_dev_synthetic_decorrelated.py` para que los ejemplos adversariales de F0 extremo también bajen jitter/shimmer y suban HNR de forma correlacionada (no solo variar F0), en vez de dejar el ruido de síntesis fijo o aleatorio sin relación con qué tan extremo es el F0. Es la versión afinada, ahora validada con datos reales, del pendiente "correlacionar severidad de jitter/shimmer con el género" que ya estaba anotado en el cierre de 4.8.

## 4.15. Implementado: fonación correlacionada con F0 extremo en `very_high`, mejora real en pruebas sintéticas

Implementación del experimento propuesto en 4.14. Solo el rango `very_high` (280-400 Hz) de `F0_RANGES` en `_dev_synthetic_decorrelated.py` ahora sintetiza con `jitter_std`/`shimmer_std`/`noise_std` reducidos (`VERY_HIGH_F0_NOISE_RANGES`, rangos angostos calibrados empíricamente, no un valor fijo, para no repetir el error de "huella digital sintética" de 4.7) en vez de los defaults de `synth_vowel()` usados para `low`/`high`. `low`/`high` no se tocaron: el hallazgo de 4.14 fue específico al registro forzado extremo, no a cualquier actuación de voz.

Regenerados los 3,000 ejemplos sintéticos decorrelacionados con esta lógica, mezclados igual que antes con los 5,000 reales (`manifest_es-mx.csv` truncado a los 5,000 reales antes de volver a pegar, para no duplicar la generación anterior), reentrenado con `--adversarial-weight 5` (el valor ya validado, no se tocó). Resultado en las métricas automáticas: accuracy general 82.6% (antes 81.7%, sin caída), prueba de estrés adversarial 85.1% (antes 85.5%, sin caída), peso de F0 30.9% (antes 31.3%). Ningún síntoma del desastre de peso 10 (sección 4.11): los casos de control sintéticos (voz masculina/femenina normal, sin extremos) siguen puntuando de forma sensata.

**Prueba dirigida al problema real:** un caso sintético de control con F0=340Hz + formantes masculinos + ruido normal (no la fonación limpia) dio 17.1; el mismo caso con la fonación anormalmente limpia confirmada en 4.14 dio 10.4, **más confiadamente masculino, no menos**. Confirma que el modelo no aprendió "F0 alto = masculino" a secas (seguiría usando los formantes con ruido normal), sino la combinación específica F0 extremo + fonación limpia como señal adicional masculina cuando coincide con formantes masculinos.

**Pendiente de confirmar con la grabación real** (aún no se ha vuelto a probar "aguda actuada" contra este modelo exportado). Antes de esto, esa combinación real (342Hz, jitter 0.63%, shimmer 3.89%, HNR 26.06, formantes que resultan ser más bien neutros esta vez) puntuaba muy femenino; falta la prueba real para confirmar si cruza. `models/crisantemo_v1.joblib` ya está exportado con este cambio.

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
