# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.9747
- F1: 0.9749
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 4.38
- Matriz de confusión: [[419, 15], [7, 428]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f0_mean_hz | 0.158 |
| shimmer_local_pct | 0.101 |
| spectral_centroid_mean_hz | 0.100 |
| f0_std_hz | 0.098 |
| f3_mean_hz | 0.092 |
| hnr_db | 0.087 |
| f0_range_semitones | 0.069 |
| f2_f1_diff_hz | 0.068 |
| f3_f2_diff_hz | 0.068 |
| jitter_local_pct | 0.058 |
| f1_mean_hz | 0.054 |
| f2_mean_hz | 0.046 |

**Peso combinado de features de F0: 32.5%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.

## Prueba de estrés: tono y resonancia decorrelacionados

Accuracy en los 60 casos donde tono y formantes van en direcciones opuestas (ej. tono agudo con formantes masculinos): **100.0%**.
OK: el modelo clasifica correctamente incluso cuando tono y resonancia no coinciden.