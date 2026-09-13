/**
 * Gráfica de línea en vivo del score suavizado. Canvas dibujado a mano, sin
 * librería de gráficas, mismo patrón que theme/discoLights.js.
 *
 * Dos suavizados distintos, no solo uno:
 * 1. La línea en sí es una curva (quadraticCurveTo por el punto medio entre
 *    cada par de puntos), no segmentos rectos con quiebres duros.
 * 2. Cada punto nuevo no salta de golpe a su valor real: hay un arreglo de
 *    valores "mostrados" que se acerca por easing exponencial al arreglo de
 *    valores "reales" cuadro a cuadro, mismo patrón que
 *    theme/discoLights.js (target + easing) pero aplicado a cada punto de
 *    la serie en vez de a un solo ángulo.
 */
const MAX_POINTS = 60;
const EASE_FACTOR = 0.18;
const EASE_EPSILON = 0.05;

function accentColor() {
  return getComputedStyle(document.body).getPropertyValue("--accent").trim() || "#B0481F";
}

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

export function createLiveGraph(canvas) {
  const ctx = canvas.getContext("2d");
  const targets = [];
  const displayed = [];
  let rafId = null;

  function resize() {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    draw();
  }

  function toXY(value, i, width, height) {
    return {
      x: (i / (MAX_POINTS - 1)) * width,
      y: height - (value / 100) * height,
    };
  }

  function drawSmoothLine(pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length - 1; i++) {
      const midX = (pts[i].x + pts[i + 1].x) / 2;
      const midY = (pts[i].y + pts[i + 1].y) / 2;
      ctx.quadraticCurveTo(pts[i].x, pts[i].y, midX, midY);
    }
    const last = pts[pts.length - 1];
    const secondLast = pts[pts.length - 2];
    ctx.quadraticCurveTo(secondLast.x, secondLast.y, last.x, last.y);
    ctx.stroke();
  }

  function draw() {
    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    // Fondo con los mismos tres tramos que el medidor de score estático:
    // celeste/blanco/rosa, la escala del score, no decorativo.
    const bg = ctx.createLinearGradient(0, height, 0, 0);
    bg.addColorStop(0, "rgba(91,206,250,0.12)");
    bg.addColorStop(0.5, "rgba(255,255,255,0.05)");
    bg.addColorStop(1, "rgba(245,169,184,0.12)");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    if (displayed.length < 2) return;

    const ratio = window.devicePixelRatio || 1;
    const pts = displayed.map((value, i) => toXY(value, i, width, height));
    ctx.strokeStyle = accentColor();
    ctx.lineWidth = 2.5 * ratio;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    if (pts.length === 2) {
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      ctx.lineTo(pts[1].x, pts[1].y);
      ctx.stroke();
    } else {
      drawSmoothLine(pts);
    }

    const lastPoint = pts[pts.length - 1];
    ctx.beginPath();
    ctx.arc(lastPoint.x, lastPoint.y, 4 * ratio, 0, Math.PI * 2);
    ctx.fillStyle = accentColor();
    ctx.fill();
  }

  function stopEasing() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function easeTowardTargets() {
    let stillMoving = false;
    for (let i = 0; i < targets.length; i++) {
      const diff = targets[i] - displayed[i];
      if (Math.abs(diff) > EASE_EPSILON) {
        displayed[i] += diff * EASE_FACTOR;
        stillMoving = true;
      } else {
        displayed[i] = targets[i];
      }
    }
    draw();
    if (stillMoving) {
      rafId = requestAnimationFrame(easeTowardTargets);
    } else {
      rafId = null;
    }
  }

  resize();
  window.addEventListener("resize", resize);

  return {
    push(score) {
      // El punto nuevo arranca su animación desde donde estaba el último
      // punto mostrado (no desde su propio valor real), así el segmento
      // nuevo se ve crecer hacia su lugar en vez de aparecer ya puesto.
      const startValue = displayed.length > 0 ? displayed[displayed.length - 1] : score;
      targets.push(score);
      displayed.push(startValue);
      if (targets.length > MAX_POINTS) {
        targets.shift();
        displayed.shift();
      }

      if (prefersReducedMotion()) {
        stopEasing();
        for (let i = 0; i < targets.length; i++) displayed[i] = targets[i];
        draw();
        return;
      }

      if (rafId === null) rafId = requestAnimationFrame(easeTowardTargets);
    },
    stop() {
      stopEasing();
      window.removeEventListener("resize", resize);
    },
  };
}
