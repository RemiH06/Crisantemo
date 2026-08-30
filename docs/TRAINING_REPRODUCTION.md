# Cómo reproducir el pipeline de entrenamiento y el reporte de evaluación

Esto documenta exactamente los pasos que se corrieron para llegar a `training/data/reports/eval_v1.md`. Sirve tanto para repetirlo con el dataset sintético de prueba como, en una máquina con internet completo, para correrlo con Mozilla Common Voice de verdad.

**Estado actual: `eval_v1.md` viene de 5,000 clips reales + 3,000 sintéticos decorrelacionados con formantes variables** (secciones 2A, 2C, 4.6, 4.7). 85.15% accuracy, F1 0.8534, peso de F0 de 25.1%, 61.6% en la prueba de estrés adversarial sintética. **Importante:** la accuracy bajó a propósito respecto a versiones anteriores (que llegaban a 98% pero "hacían trampa", ver sección 4.7); el modelo actual mejora de verdad en voz actuada real (ver sección 4.8) pero **no lo resuelve del todo**, sigue sin resolverse por completo. No lo omitas si vas a confiar en este modelo para algo serio. Sesión en pausa aquí, continúa desde la sección 4.8.

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
