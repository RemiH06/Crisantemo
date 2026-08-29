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
 */
export function renderScoreMeter(score) {
  const clamped = Math.max(0, Math.min(100, score));
  return `
    <div class="score-meter">
      <div class="score-meter-track" aria-hidden="true">
        <div class="score-meter-marker" style="left:${clamped}%"></div>
      </div>
      <div class="score-meter-value" aria-hidden="true">
        ${clamped.toFixed(0)}<span class="score-meter-max">/100</span>
      </div>
      <span class="sr-only">Puntuación: ${clamped.toFixed(0)} de 100</span>
    </div>
  `;
}
