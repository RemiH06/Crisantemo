/**
 * Gráfica de línea en vivo del score suavizado. Canvas dibujado a mano, sin
 * librería de gráficas, mismo patrón que theme/discoLights.js.
 */
const MAX_POINTS = 60;

function accentColor() {
  return getComputedStyle(document.body).getPropertyValue("--accent").trim() || "#D94F3A";
}

export function createLiveGraph(canvas) {
  const ctx = canvas.getContext("2d");
  const points = [];

  function resize() {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    draw();
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

    if (points.length < 2) return;

    const ratio = window.devicePixelRatio || 1;
    ctx.beginPath();
    points.forEach((score, i) => {
      const x = (i / (MAX_POINTS - 1)) * width;
      const y = height - (score / 100) * height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = accentColor();
    ctx.lineWidth = 2.5 * ratio;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    const lastScore = points[points.length - 1];
    const lastX = ((points.length - 1) / (MAX_POINTS - 1)) * width;
    const lastY = height - (lastScore / 100) * height;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4 * ratio, 0, Math.PI * 2);
    ctx.fillStyle = accentColor();
    ctx.fill();
  }

  resize();
  window.addEventListener("resize", resize);

  return {
    push(score) {
      points.push(score);
      if (points.length > MAX_POINTS) points.shift();
      draw();
    },
    stop() {
      window.removeEventListener("resize", resize);
    },
  };
}
