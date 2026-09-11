# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.7948
- F1: 0.7823
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 25.41
- Matriz de confusión: [[511, 88], [158, 442]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f0_mean_hz | 0.179 |
| hnr_db | 0.126 |
| spectral_centroid_mean_hz | 0.123 |
| f1_mean_hz | 0.113 |
| f3_mean_hz | 0.086 |
| f0_range_semitones | 0.078 |
| f2_mean_hz | 0.066 |
| shimmer_local_pct | 0.065 |
| jitter_local_pct | 0.051 |
| f0_std_hz | 0.045 |
| f2_f1_diff_hz | 0.039 |
| f3_f2_diff_hz | 0.029 |

**Peso combinado de features de F0: 30.1%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.

## Prueba de estrés: tono y resonancia decorrelacionados

Accuracy en los 242 casos donde tono y formantes van en direcciones opuestas (ej. tono agudo con formantes masculinos): **91.7%**.
OK: el modelo clasifica correctamente incluso cuando tono y resonancia no coinciden.