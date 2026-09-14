# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.8263
- F1: 0.8219
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 23.05
- Matriz de confusión: [[495, 87], [115, 466]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f0_mean_hz | 0.173 |
| hnr_db | 0.120 |
| spectral_centroid_mean_hz | 0.106 |
| f1_mean_hz | 0.096 |
| shimmer_local_pct | 0.086 |
| f3_mean_hz | 0.084 |
| f0_range_semitones | 0.082 |
| f2_mean_hz | 0.072 |
| jitter_local_pct | 0.057 |
| f0_std_hz | 0.053 |
| f2_f1_diff_hz | 0.040 |
| f3_f2_diff_hz | 0.031 |

**Peso combinado de features de F0: 30.9%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.

## Prueba de estrés: tono y resonancia decorrelacionados

Accuracy en los 235 casos donde tono y formantes van en direcciones opuestas (ej. tono agudo con formantes masculinos): **85.1%**.
OK: el modelo clasifica correctamente incluso cuando tono y resonancia no coinciden.