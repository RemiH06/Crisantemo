import { describe, expect, it } from "vitest";
import { renderScoreMeter } from "./scoreMeter.js";

// El marcador y el número visibles siempre arrancan en 0 (animateScoreMeter
// los anima al valor real después de insertarse en el DOM, ver app.js); el
// valor final vive en data-target-score y en el texto sr-only, que sí es
// correcto desde el primer render (lectores de pantalla no esperan la
// animación). animateScoreMeter en sí no tiene test unitario: usa DOM real
// (requestAnimationFrame, matchMedia), igual que audio/theme, que tampoco
// lo tienen todavía (necesitarían jsdom).
describe("renderScoreMeter", () => {
  it("carries the rounded score in data-target-score and the sr-only text", () => {
    const html = renderScoreMeter(72.4);
    expect(html).toContain('data-target-score="72.4"');
    expect(html).toContain("Puntuación: 72 de 100");
  });

  it("clamps a score above 100 down to 100", () => {
    const html = renderScoreMeter(140);
    expect(html).toContain('data-target-score="100"');
    expect(html).toContain("Puntuación: 100 de 100");
  });

  it("clamps a negative score up to 0", () => {
    const html = renderScoreMeter(-15);
    expect(html).toContain('data-target-score="0"');
    expect(html).toContain("Puntuación: 0 de 100");
  });

  it("starts the visible marker and number at 0, regardless of the score", () => {
    const html = renderScoreMeter(33);
    expect(html).toContain('left:0%');
    expect(html).toContain('<span class="score-meter-number">0</span>');
  });
});
