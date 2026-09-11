/**
 * Fondo de "luces disco": círculos de luz difusos que flotan lentamente
 * sobre un <canvas>. Tomado tal cual del demo de tema (disco_theme_demo.html),
 * solo envuelto en una función para poder inicializarlo desde main.js.
 *
 * Paleta de crisantemo: 6 de las 8 luces son tonos reales de la flor (oro,
 * bronce, óxido, magenta, lavanda, musgo); las otras 2 son los tonos exactos
 * de la bandera trans (#5BCEFA / #F5A9B8, los mismos que ya usan el logo y
 * el medidor de score), no floral a propósito. Si se cambia la paleta en
 * theme.css (--gold, --bronze, etc.), hay que actualizar también estos
 * arreglos a mano: son RGB planos para el canvas, no leen custom properties.
 */

const LIGHTS_LIGHT = [
  { r: 176, g: 72, b: 31 }, // rust -> #B0481F
  { r: 133, g: 96, b: 184 }, // lavender -> #8560B8
  { r: 91, g: 122, b: 58 }, // moss -> #5B7A3A
  { r: 217, g: 163, b: 44 }, // gold -> #D9A32C
  { r: 178, g: 51, b: 104 }, // magenta -> #B23368
  { r: 194, g: 112, b: 30 }, // bronze -> #C2701E
  { r: 91, g: 206, b: 250 }, // flag-blue -> #5BCEFA (bandera trans)
  { r: 245, g: 169, b: 184 }, // flag-blush -> #F5A9B8 (bandera trans)
];

const LIGHTS_DARK = [
  { r: 224, g: 106, b: 58 }, // rust -> #E06A3A
  { r: 164, g: 127, b: 219 }, // lavender -> #A47FDB
  { r: 123, g: 163, b: 90 }, // moss -> #7BA35A
  { r: 240, g: 187, b: 70 }, // gold -> #F0BB46
  { r: 212, g: 92, b: 140 }, // magenta -> #D45C8C
  { r: 224, g: 140, b: 62 }, // bronze -> #E08C3E
  { r: 91, g: 206, b: 250 }, // flag-blue -> #5BCEFA (bandera trans, ya suficientemente clara para fondo oscuro)
  { r: 245, g: 169, b: 184 }, // flag-blush -> #F5A9B8 (bandera trans)
];

function makeLights(cols) {
  return cols.map((c, i) => {
    const angle = ((Math.PI * 2) / cols.length) * i;
    return {
      x: 0.5,
      y: 0.5,
      vx: Math.cos(angle) * 0.0008 + (Math.random() - 0.5) * 0.0004,
      vy: Math.sin(angle) * 0.0008 + (Math.random() - 0.5) * 0.0004,
      radius: 0.28 + Math.random() * 0.15,
      r: c.r,
      g: c.g,
      b: c.b,
      opacity: 0.18 + Math.random() * 0.12,
    };
  });
}

/**
 * Inicia la animación sobre el canvas dado. Se detiene sola si el canvas
 * se quita del DOM (requestAnimationFrame simplemente deja de tener sentido,
 * pero por prolijidad se expone una función de cleanup).
 *
 * Respeta prefers-reduced-motion: en vez del loop de animación, dibuja un
 * solo cuadro estático (las luces siguen visibles, pero no se mueven). Si el
 * usuario cambia esa preferencia del sistema en vivo, reacciona sin recargar.
 */
export function initDiscoLights(canvas) {
  const ctx = canvas.getContext("2d");
  let width;
  let height;
  let rafId = null;

  const lights = makeLights(LIGHTS_LIGHT);
  const reducedMotionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)");

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    renderFrame(false);
  }

  function renderFrame(animate) {
    ctx.clearRect(0, 0, width, height);
    const isDark = document.body.classList.contains("dark");
    const cols = isDark ? LIGHTS_DARK : LIGHTS_LIGHT;

    for (let i = 0; i < lights.length; i++) {
      const l = lights[i];
      const c = cols[i];

      if (animate) {
        l.x += l.vx;
        l.y += l.vy;
        if (l.x < -0.1) l.vx = Math.abs(l.vx);
        if (l.x > 1.1) l.vx = -Math.abs(l.vx);
        if (l.y < -0.1) l.vy = Math.abs(l.vy);
        if (l.y > 1.1) l.vy = -Math.abs(l.vy);
      }

      const px = l.x * width;
      const py = l.y * height;
      const rad = l.radius * Math.min(width, height);

      const gradient = ctx.createRadialGradient(px, py, 0, px, py, rad);
      gradient.addColorStop(0, `rgba(${c.r},${c.g},${c.b},${l.opacity})`);
      gradient.addColorStop(0.5, `rgba(${c.r},${c.g},${c.b},${l.opacity * 0.4})`);
      gradient.addColorStop(1, `rgba(${c.r},${c.g},${c.b},0)`);

      ctx.beginPath();
      ctx.arc(px, py, rad, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
    }
  }

  function loop() {
    renderFrame(true);
    rafId = requestAnimationFrame(loop);
  }

  function stopLoop() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function start() {
    stopLoop();
    if (reducedMotionQuery?.matches) {
      renderFrame(false);
    } else {
      rafId = requestAnimationFrame(loop);
    }
  }

  resize();
  window.addEventListener("resize", resize);
  reducedMotionQuery?.addEventListener?.("change", start);
  start();

  return function stop() {
    stopLoop();
    window.removeEventListener("resize", resize);
    reducedMotionQuery?.removeEventListener?.("change", start);
  };
}
