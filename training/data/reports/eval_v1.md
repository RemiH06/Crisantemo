# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.9467
- F1: 0.9429
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 6.76
- Matriz de confusión: [[38, 0], [4, 33]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f0_mean_hz | 0.212 |
| shimmer_local_pct | 0.185 |
| spectral_centroid_mean_hz | 0.109 |
| f0_std_hz | 0.079 |
| f3_mean_hz | 0.078 |
| f1_mean_hz | 0.067 |
| f2_mean_hz | 0.056 |
| jitter_local_pct | 0.054 |
| f2_f1_diff_hz | 0.050 |
| f0_range_semitones | 0.045 |
| hnr_db | 0.033 |
| f3_f2_diff_hz | 0.031 |

**Peso combinado de features de F0: 33.7%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.