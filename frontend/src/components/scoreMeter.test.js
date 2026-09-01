import { describe, expect, it } from "vitest";
import { renderScoreMeter } from "./scoreMeter.js";

describe("renderScoreMeter", () => {
  it("shows the score rounded, and the sr-only text with it", () => {
    const html = renderScoreMeter(72.4);
    expect(html).toMatch(/72\s*<span class="score-meter-max">/);
    expect(html).toContain("Puntuación: 72 de 100");
  });

  it("clamps a score above 100 down to 100", () => {
    const html = renderScoreMeter(140);
    expect(html).toContain("left:100%");
    expect(html).toContain("Puntuación: 100 de 100");
  });

  it("clamps a negative score up to 0", () => {
    const html = renderScoreMeter(-15);
    expect(html).toContain("left:0%");
    expect(html).toContain("Puntuación: 0 de 100");
  });

  it("positions the marker at the score's percentage", () => {
    const html = renderScoreMeter(33);
    expect(html).toContain("left:33%");
  });
});
