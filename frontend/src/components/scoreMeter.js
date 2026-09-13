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
        <span class="score-meter-petals"></span>
      </div>
      <span class="sr-only">Puntuación: ${clamped.toFixed(0)} de 100</span>
    </div>
  `;
}

// Tonos florales para los pétalos del acento de floración (ver
// spawnPetalBurst). Los mismos 7 tokens de theme.css, no colores nuevos.
const PETAL_COLOR_VARS = ["--gold", "--bronze", "--rust", "--wine", "--magenta", "--lavender", "--moss"];
const PETAL_COUNT = 6;

/**
 * Dispersa unos pocos pétalos desde el número del score al momento de
 * florecer, como si el propio medidor fuera la flor abriéndose. Puramente
 * festivo (no aria-hidden porque su contenedor ya lo es), así que se omite
 * por completo con prefers-reduced-motion en vez de solo acortar la
 * duración: no comunica nada esencial, es el único lugar de la app donde
 * eso es aceptable saltarse entero.
 */
function spawnPetalBurst(container) {
  if (!container) return;
  const bodyStyles = getComputedStyle(document.body);
  for (let i = 0; i < PETAL_COUNT; i++) {
    const petal = document.createElement("div");
    petal.className = "score-meter-petal";
    const angle = (360 / PETAL_COUNT) * i + (Math.random() * 26 - 13);
    const distance = 26 + Math.random() * 18;
    const rad = (angle * Math.PI) / 180;
    petal.style.setProperty("--petal-dx", `${(Math.cos(rad) * distance).toFixed(1)}px`);
    petal.style.setProperty("--petal-dy", `${(Math.sin(rad) * distance).toFixed(1)}px`);
    petal.style.setProperty("--petal-rot", `${(Math.random() * 180 - 90).toFixed(0)}deg`);
    petal.style.background = bodyStyles.getPropertyValue(PETAL_COLOR_VARS[i % PETAL_COLOR_VARS.length]).trim();
    container.appendChild(petal);
    petal.addEventListener("transitionend", () => petal.remove(), { once: true });
  }
  // Una sola clase después de insertar todos: dispara la transición de cada
  // uno desde su estado de reposo (0 en CSS) sin que el primero ya se haya
  // movido antes de que el último termine de insertarse.
  requestAnimationFrame(() => {
    container.querySelectorAll(".score-meter-petal").forEach((p) => p.classList.add("is-drifting"));
  });
}

/**
 * Anima el marcador y el número de 0 al score real. Llamar una vez, después
 * de que el HTML de renderScoreMeter() ya esté en el DOM. Respeta
 * prefers-reduced-motion: salta directo al valor final sin contar (el
 * marcador de todas formas no se mueve de más, la transición CSS de
 * .score-meter-marker ya se colapsa globalmente en ese caso) y omite del
 * todo el acento de pétalos.
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

  spawnPetalBurst(meter.querySelector(".score-meter-petals"));

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
