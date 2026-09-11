/**
 * Barras de nivel de audio en vivo mientras se graba: reaccionan a volumen y
 * contenido espectral del micrófono en tiempo real. Es retroalimentación
 * visual de que el micrófono está captando algo, no un análisis acústico
 * real (eso lo hace el backend con parselmouth); no debe confundirse con el
 * score ni con las features de /api/v1/analyze. El verdadero análisis en
 * vivo (pitch/formantes reales mientras se habla) es Fase 4, sin empezar.
 *
 * Puramente decorativo: el canvas es aria-hidden, el estado de "grabando"
 * ya se anuncia aparte por texto. Respeta prefers-reduced-motion mostrando
 * un indicador estático en vez de barras animadas.
 */
const BAR_COUNT = 24;

function themeAccentColor() {
  return getComputedStyle(document.body).getPropertyValue("--accent").trim() || "#B0481F";
}

function sizeCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * ratio;
  canvas.height = canvas.clientHeight * ratio;
}

function drawBars(ctx, width, height, heights) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = themeAccentColor();
  const barWidth = width / BAR_COUNT;
  for (let i = 0; i < BAR_COUNT; i++) {
    const barHeight = heights[i];
    ctx.fillRect(i * barWidth + barWidth * 0.15, height - barHeight, barWidth * 0.7, barHeight);
  }
}

function staticFallback(canvas) {
  sizeCanvas(canvas);
  const ctx = canvas.getContext("2d");
  const heights = new Array(BAR_COUNT).fill(canvas.height * 0.22);
  drawBars(ctx, canvas.width, canvas.height, heights);
  return () => {};
}

/**
 * Empieza a dibujar las barras a partir del stream de micrófono ya abierto
 * (el mismo que usa el grabador). Regresa una función de limpieza.
 */
export function createLevelVisualizer(stream, canvas) {
  const reducedMotionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  if (reducedMotionQuery?.matches) {
    return staticFallback(canvas);
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return staticFallback(canvas);
  }

  const audioCtx = new AudioContextClass();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 128;
  analyser.smoothingTimeConstant = 0.75;
  source.connect(analyser);

  const data = new Uint8Array(analyser.frequencyBinCount);
  const step = Math.max(1, Math.floor(data.length / BAR_COUNT));
  const ctx = canvas.getContext("2d");
  let rafId = null;

  function resize() {
    sizeCanvas(canvas);
  }

  function loop() {
    analyser.getByteFrequencyData(data);
    const heights = new Array(BAR_COUNT);
    for (let i = 0; i < BAR_COUNT; i++) {
      const value = data[i * step] / 255;
      heights[i] = Math.max(3, value * canvas.height);
    }
    drawBars(ctx, canvas.width, canvas.height, heights);
    rafId = requestAnimationFrame(loop);
  }

  resize();
  window.addEventListener("resize", resize);
  rafId = requestAnimationFrame(loop);

  return function stop() {
    if (rafId !== null) cancelAnimationFrame(rafId);
    window.removeEventListener("resize", resize);
    source.disconnect();
    audioCtx.close().catch(() => {});
  };
}
