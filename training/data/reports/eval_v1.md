# Reporte de evaluación: crisantemo_v1

- Accuracy: 0.8515
- F1: 0.8534
- MAE (score continuo 0-100 vs. etiqueta binaria*100): 20.16
- Matriz de confusión: [[503, 96], [82, 518]]

## Importancia de features

| Feature | Importancia |
|---|---|
| hnr_db | 0.139 |
| f1_mean_hz | 0.113 |
| f0_mean_hz | 0.113 |
| spectral_centroid_mean_hz | 0.099 |
| f2_mean_hz | 0.089 |
| f3_mean_hz | 0.089 |
| shimmer_local_pct | 0.084 |
| f0_range_semitones | 0.079 |
| jitter_local_pct | 0.076 |
| f0_std_hz | 0.059 |
| f2_f1_diff_hz | 0.032 |
| f3_f2_diff_hz | 0.028 |

**Peso combinado de features de F0: 25.1%**

OK: el modelo no depende desproporcionadamente del pitch; usa formantes y otras features de resonancia de forma significativa.

## Prueba de estrés: tono y resonancia decorrelacionados

Accuracy en los 242 casos donde tono y formantes van en direcciones opuestas (ej. tono agudo con formantes masculinos): **61.6%**.
ADVERTENCIA: por debajo de 70%. El modelo sigue usando el tono como atajo en vez de la resonancia en estos casos, que es justo lo que el proyecto busca evitar.