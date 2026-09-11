/**
 * Medidor de score 0-100. No depende solo de color para comunicar el
 * resultado (accesibilidad, daltonismo): el número siempre está escrito, y
 * la posición en la barra tiene un marcador con forma propia, no solo un
 * cambio de tono. El texto que describe la percepción (masculina/andrógina/
 * femenina) lo pone quien llama esto, con feedback.summary del backend, no
 * este componente (una sola fuente de verdad para esa clasificación).
 *
 * El degradado de la barra usa los colores de la bandera trans (celeste,
 * blanco, rosa) de un extremo al otro: no es decorativo, es la escala misma
 * que el score representa.
 *
 * Se dibuja en 0 (marcador e indicador visual) y sube al valor real vía
 * animateScoreMeter(), llamado después de insertar este HTML en el DOM. El
 * texto para lector de pantalla (sr-only) ya lleva el valor final desde el
 * primer render, no espera a la animación.
 */
export function renderScoreMeter(score) {
  const clamped = Math.max(0, Math.min(100, score));
  return `
    <div class="score-meter" data-target-score="${clamped}">
      <div class="score-meter-track" aria-hidden="true">
        <div class="score-meter-marker" style="left:0%"></div>
      </div>
      <div class="score-meter-value" aria-hidden="true">
        <span class="score-meter-number">0</span><span class="score-meter-max">/100</span>
      </div>
      <span class="sr-only">Puntuación: ${clamped.toFixed(0)} de 100</span>
    </div>
  `;
}

/**
 * Anima el marcador y el número de 0 al score real. Llamar una vez, después
 * de que el HTML de renderScoreMeter() ya esté en el DOM. Respeta
 * prefers-reduced-motion: salta directo al valor final sin contar (el
 * marcador de todas formas no se mueve de más, la transición CSS de
 * .score-meter-marker ya se colapsa globalmente en ese caso).
 */
export function animateScoreMeter(root) {
  const meter = root.querySelector(".score-meter");
  if (!meter) return;
  const target = parseFloat(meter.dataset.targetScore);
  const marker = meter.querySelector(".score-meter-marker");
  const numberEl = meter.querySelector(".score-meter-number");

  requestAnimationFrame(() => {
    marker.style.left = `${target}%`;
  });

  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  if (reduceMotion) {
    numberEl.textContent = target.toFixed(0);
    return;
  }

  const durationMs = 700;
  const startTime = performance.now();
  function tick(now) {
    const progress = Math.min(1, (now - startTime) / durationMs);
    const eased = 1 - Math.pow(1 - progress, 3);
    numberEl.textContent = (target * eased).toFixed(0);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
