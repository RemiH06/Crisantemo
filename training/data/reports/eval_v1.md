# Reporte de evaluación: crisantemo_v1

- Accuracy: 1.0000
- F1: 1.0000
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 0.43
- Matriz de confusión: [[23, 0], [0, 22]]

## Importancia de features

| Feature | Importancia |
|---|---|
| f3_mean_hz | 0.164 |
| f2_mean_hz | 0.152 |
| spectral_centroid_mean_hz | 0.149 |
| f2_f1_diff_hz | 0.143 |
| f0_mean_hz | 0.125 |
| f3_f2_diff_hz | 0.061 |
| f1_mean_hz | 0.052 |
| jitter_local_pct | 0.038 |
| hnr_db | 0.036 |
| shimmer_local_pct | 0.033 |
| f0_std_hz | 0.025 |
| f0_range_semitones | 0.024 |

**Peso combinado de features de F0: 17.4%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.