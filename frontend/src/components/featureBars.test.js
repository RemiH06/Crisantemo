import { describe, expect, it } from "vitest";
import { renderFeatureBars } from "./featureBars.js";

const BASE_FEATURES = {
  f0_mean_hz: 200,
  f0_std_hz: 25,
  f0_range_semitones: 12,
  f1_mean_hz: 500,
  f2_mean_hz: 1600,
  f3_mean_hz: 2700,
  f2_f1_diff_hz: 1000,
  f3_f2_diff_hz: 1000,
  jitter_local_pct: 1.5,
  shimmer_local_pct: 5,
  hnr_db: 15,
  spectral_centroid_mean_hz: 1800,
};

describe("renderFeatureBars", () => {
  it("renders a row for all 12 features with their real value shown", () => {
    const html = renderFeatureBars(BASE_FEATURES);
    expect(html).toContain("Tono promedio (F0)");
    expect(html).toContain("Formante F3");
    expect(html).toContain("Claridad (HNR)");
    expect(html).toContain("15.00");
  });

  it("fills the bar proportionally within the feature's range", () => {
    // f0_mean_hz: min 50, max 350 -> 200 está justo a la mitad
    const html = renderFeatureBars({ ...BASE_FEATURES, f0_mean_hz: 200 });
    expect(html).toContain("width:50.0%");
  });

  it("clamps the fill to 0% when the value is below the range's minimum", () => {
    const html = renderFeatureBars({ ...BASE_FEATURES, hnr_db: -10 });
    expect(html).toContain("width:0.0%");
    // el valor real sigue mostrándose tal cual, no se recorta
    expect(html).toContain("-10.00");
  });

  it("clamps the fill to 100% when the value is above the range's maximum", () => {
    const html = renderFeatureBars({ ...BASE_FEATURES, jitter_local_pct: 999 });
    expect(html).toContain("width:100.0%");
    expect(html).toContain("999.00");
  });
});
