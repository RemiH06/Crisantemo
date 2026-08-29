import "./styles/theme.css";
import { initDiscoLights } from "./theme/discoLights.js";
import { initAsanohaBackground } from "./theme/asanohaBackground.js";
import { initThemeToggle } from "./theme/themeToggle.js";

const app = document.getElementById("app");

app.innerHTML = `
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:48px">
    <h1>crisantemo</h1>
    <button class="theme-btn" id="toggle-btn">◐ oscuro</button>
  </div>

  <div class="callout warn">
    <div class="callout-title">Vista previa del tema</div>
    <p>
      Esto es solo el andamiaje visual (fondo animado, tokens de color, componentes base) tomado del
      demo de tema. Las pantallas reales (grabar/subir audio, ver la puntuación, modo en vivo) se
      construyen en la Fase 3, sobre esta misma base.
    </p>
  </div>

  <h2>Ejemplo: cómo se vería una puntuación</h2>
  <div class="card">
    <div class="metrics-row">
      <div class="metric">
        <div class="metric-val">72</div>
        <div class="metric-lbl">puntuación (0-100)</div>
      </div>
      <div class="metric">
        <div class="metric-val" style="color:var(--sky)">198 Hz</div>
        <div class="metric-lbl">tono promedio</div>
      </div>
      <div class="metric">
        <div class="metric-val" style="color:var(--lila)">1620 Hz</div>
        <div class="metric-lbl">F2 promedio</div>
      </div>
    </div>
  </div>

  <h2>Ejemplo: pasos de grabación</h2>
  <div class="onboard-row">
    <div class="onboard-num">1</div>
    <div>
      <h4>Busca un lugar silencioso</h4>
      <p class="muted">Sin ruido de fondo, el análisis es más confiable.</p>
    </div>
  </div>
  <div class="onboard-row">
    <div class="onboard-num">2</div>
    <div>
      <h4>Habla por al menos 3-5 segundos</h4>
      <p class="muted">Frases con variación de entonación funcionan mejor que un tono plano.</p>
    </div>
  </div>
`;

initThemeToggle(document.getElementById("toggle-btn"));
initDiscoLights(document.getElementById("disco-lights"));
initAsanohaBackground(document.querySelector(".asanoha-bg"));
