/**
 * Desglose visual de las 12 features acústicas, una barra por feature en vez
 * de una tabla de números pelones. Los rangos min/max de cada barra son solo
 * para darle una escala razonable al dibujo (qué tanto se llena la barra),
 * no son umbrales clínicos ni el cálculo real del score (eso lo hace el
 * modelo en el backend con el vector completo, no una feature a la vez).
 */
const FEATURE_META = {
  f0_mean_hz: { label: "Tono promedio (F0)", unit: "Hz", min: 50, max: 350 },
  f0_std_hz: { label: "Variación de tono", unit: "Hz", min: 0, max: 50 },
  f0_range_semitones: { label: "Rango de tono", unit: "semitonos", min: 0, max: 24 },
  f1_mean_hz: { label: "Formante F1", unit: "Hz", min: 200, max: 1000 },
  f2_mean_hz: { label: "Formante F2", unit: "Hz", min: 800, max: 2500 },
  f3_mean_hz: { label: "Formante F3", unit: "Hz", min: 2000, max: 3500 },
  f2_f1_diff_hz: { label: "Espaciado F2-F1", unit: "Hz", min: 0, max: 2000 },
  f3_f2_diff_hz: { label: "Espaciado F3-F2", unit: "Hz", min: 0, max: 2000 },
  jitter_local_pct: { label: "Jitter", unit: "%", min: 0, max: 3 },
  shimmer_local_pct: { label: "Shimmer", unit: "%", min: 0, max: 10 },
  hnr_db: { label: "Claridad (HNR)", unit: "dB", min: 0, max: 30 },
  spectral_centroid_mean_hz: { label: "Brillo espectral", unit: "Hz", min: 500, max: 4000 },
};

function clampRatio(value, min, max) {
  if (max === min) return 0;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

export function renderFeatureBars(features) {
  const rows = Object.entries(FEATURE_META)
    .map(([name, meta]) => {
      const value = features[name];
      const ratio = clampRatio(value, meta.min, meta.max);
      return `
        <div class="feature-bar-row">
          <div class="feature-bar-label">${meta.label}</div>
          <div class="feature-bar-track" aria-hidden="true">
            <div class="feature-bar-fill" style="width:${(ratio * 100).toFixed(1)}%"></div>
          </div>
          <div class="feature-bar-value">${value.toFixed(2)} <span class="feature-bar-unit">${meta.unit}</span></div>
        </div>
      `;
    })
    .join("");
  return `<div class="feature-bars">${rows}</div>`;
}
