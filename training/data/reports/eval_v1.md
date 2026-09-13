# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.8173
- F1: 0.8101
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 23.75
- Matriz de confusión: [[513, 86], [133, 467]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f0_mean_hz | 0.173 |
| hnr_db | 0.137 |
| f1_mean_hz | 0.112 |
| spectral_centroid_mean_hz | 0.098 |
| f0_range_semitones | 0.078 |
| f2_mean_hz | 0.078 |
| f3_mean_hz | 0.077 |
| shimmer_local_pct | 0.068 |
| f0_std_hz | 0.062 |
| jitter_local_pct | 0.057 |
| f2_f1_diff_hz | 0.035 |
| f3_f2_diff_hz | 0.026 |

**Peso combinado de features de F0: 31.3%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.

## Prueba de estrés: tono y resonancia decorrelacionados

Accuracy en los 242 casos donde tono y formantes van en direcciones opuestas (ej. tono agudo con formantes masculinos): **85.5%**.
OK: el modelo clasifica correctamente incluso cuando tono y resonancia no coinciden.