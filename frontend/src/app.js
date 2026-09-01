/**
 * Estado y vistas de la app: grabar/subir audio, analizarlo, mostrar el
 * resultado. Sin framework (vanilla JS + Vite, ver decisión en CLAUDE.md),
 * un pequeño manejo de estado con re-render completo de un contenedor.
 *
 * El timer de grabación es la única excepción: se actualiza directo en el
 * DOM cada segundo (no dispara un re-render completo), para no perder foco
 * ni reconstruir el DOM 60 veces por minuto sin necesidad.
 */
import { analyzeAudio, AnalyzeError } from "./api/client.js";
import { createRecorder, MicrophoneError } from "./audio/recorder.js";
import { createLevelVisualizer } from "./audio/visualizer.js";
import { startLiveStream, LiveStreamError } from "./audio/liveStream.js";
import { renderScoreMeter } from "./components/scoreMeter.js";
import { renderFeatureBars } from "./components/featureBars.js";
import { createLiveGraph } from "./components/liveGraph.js";

const FEATURE_LABELS = {
  f0_mean_hz: "Tono promedio",
  f1_mean_hz: "F1 promedio",
  f2_mean_hz: "F2 promedio",
  f3_mean_hz: "F3 promedio",
  f2_f1_diff_hz: "Espaciado F2-F1",
  hnr_db: "Claridad (HNR)",
};
const PRIMARY_FEATURES = ["f0_mean_hz", "f2_f1_diff_hz", "hnr_db"];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

export function initApp(root) {
  let state = { view: "idle" };
  let activeRecorder = null;
  let elapsedTimerId = null;
  let elapsedSeconds = 0;
  let stopVisualizer = null;
  let stopLiveStreamFn = null;
  let liveGraph = null;

  function setState(next) {
    if (elapsedTimerId) {
      clearInterval(elapsedTimerId);
      elapsedTimerId = null;
    }
    if (stopVisualizer) {
      stopVisualizer();
      stopVisualizer = null;
    }
    if (stopLiveStreamFn) {
      stopLiveStreamFn();
      stopLiveStreamFn = null;
    }
    if (liveGraph) {
      liveGraph.stop();
      liveGraph = null;
    }
    if (state.view === "result" && state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }
    state = next;
    render();
  }

  function announce(message) {
    const liveRegion = document.getElementById("app-live-region");
    if (liveRegion && message) liveRegion.textContent = message;
  }

  async function handleRecordClick() {
    try {
      activeRecorder = await createRecorder();
    } catch (err) {
      if (err instanceof MicrophoneError) {
        setState({ view: "error", message: err.message });
        return;
      }
      throw err;
    }
    activeRecorder.start();
    elapsedSeconds = 0;
    setState({ view: "recording" });

    const canvas = document.getElementById("voice-bars");
    if (canvas) stopVisualizer = createLevelVisualizer(activeRecorder.stream, canvas);

    elapsedTimerId = setInterval(() => {
      elapsedSeconds += 1;
      const label = document.getElementById("elapsed-time");
      if (label) label.textContent = formatElapsed(elapsedSeconds);
    }, 1000);
  }

  async function handleStopClick() {
    if (!activeRecorder) return;
    const blob = await activeRecorder.stop();
    activeRecorder = null;
    await runAnalysis(blob, "grabacion.webm");
  }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    await runAnalysis(file, file.name);
  }

  async function handleLiveClick() {
    setState({ view: "live" });
    const canvas = document.getElementById("live-graph");
    if (canvas) liveGraph = createLiveGraph(canvas);

    try {
      stopLiveStreamFn = await startLiveStream({
        onUpdate: (data) => {
          liveGraph?.push(data.score_smoothed);
          const valueEl = document.getElementById("live-score-value");
          if (valueEl) valueEl.textContent = Math.round(data.score_smoothed);
        },
        onError: () => {
          setState({ view: "error", message: "Se perdió la conexión del modo en vivo. Intenta de nuevo." });
        },
      });
    } catch (err) {
      if (err instanceof LiveStreamError) {
        setState({ view: "error", message: err.message });
        return;
      }
      throw err;
    }
  }

  function handleStopLiveClick() {
    setState({ view: "idle" });
  }

  async function runAnalysis(blob, filename) {
    setState({ view: "analyzing" });
    try {
      const result = await analyzeAudio(blob, filename);
      const audioUrl = URL.createObjectURL(blob);
      setState({ view: "result", result, audioUrl });
    } catch (err) {
      if (err instanceof AnalyzeError) {
        setState({ view: "error", message: err.message });
        return;
      }
      setState({ view: "error", message: "Algo falló de nuestro lado, intenta de nuevo en un momento." });
    }
  }

  function wireEvents() {
    document.getElementById("record-btn")?.addEventListener("click", handleRecordClick);
    document.getElementById("stop-btn")?.addEventListener("click", handleStopClick);
    document.getElementById("upload-btn")?.addEventListener("click", () => {
      document.getElementById("upload-input")?.click();
    });
    document.getElementById("upload-input")?.addEventListener("change", handleFileSelected);
    document.getElementById("retry-btn")?.addEventListener("click", () => setState({ view: "idle" }));
    document.getElementById("record-again-btn")?.addEventListener("click", () => setState({ view: "idle" }));
    document.getElementById("live-btn")?.addEventListener("click", handleLiveClick);
    document.getElementById("stop-live-btn")?.addEventListener("click", handleStopLiveClick);
  }

  function render() {
    root.innerHTML = viewFor(state);
    wireEvents();
    announce(statusMessageFor(state));
  }

  render();
}

function formatElapsed(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function statusMessageFor(state) {
  switch (state.view) {
    case "recording":
      return "Grabando.";
    case "live":
      return "Modo en vivo iniciado.";
    case "analyzing":
      return "Analizando tu grabación.";
    case "result":
      return "Resultado listo.";
    case "error":
      return state.message;
    default:
      return "";
  }
}

function viewFor(state) {
  switch (state.view) {
    case "recording":
      return recordingView();
    case "live":
      return liveView();
    case "analyzing":
      return analyzingView();
    case "result":
      return resultView(state.result, state.audioUrl);
    case "error":
      return errorView(state.message);
    default:
      return idleView();
  }
}

function idleView() {
  return `
    <div class="callout">
      <div class="callout-title">Antes de empezar</div>
      <p>
        Esto es una herramienta de práctica y retroalimentación, no un diagnóstico. La puntuación
        no mide qué tan válida es tu voz ni tu identidad: cada quien encuentra y desarrolla su voz
        en su propio tiempo. No guardamos tu grabación, el análisis ocurre y se olvida.
      </p>
      <p>
        El modelo todavía se está afinando: funciona mejor con tu voz de todos los días que con
        cambios muy bruscos de tono de un momento a otro. Si haces un cambio dramático, el
        resultado puede ser menos confiable. Vamos mejorando esto con el tiempo.
      </p>
    </div>

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

    <div class="card action-row">
      <button class="btn primary" id="record-btn" type="button">● Grabar mi voz</button>
      <button class="btn" id="upload-btn" type="button">Subir un archivo de audio</button>
      <button class="btn" id="live-btn" type="button">▶ Modo en vivo</button>
      <input type="file" id="upload-input" accept="audio/*" hidden />
    </div>
  `;
}

function liveView() {
  return `
    <div class="card">
      <canvas id="live-graph" class="live-graph" aria-hidden="true"></canvas>
      <div class="action-row" style="margin-top:12px">
        <p>Score en vivo: <span id="live-score-value" class="mono-time">…</span></p>
        <button class="btn primary" id="stop-live-btn" type="button">■ Detener</button>
      </div>
    </div>
    <p class="muted">
      El score se suaviza para no saltar de golpe; tarda unos segundos en estabilizarse. El audio
      no se guarda, se analiza en el momento igual que una grabación normal.
    </p>
  `;
}

function recordingView() {
  return `
    <div class="card">
      <canvas id="voice-bars" class="voice-bars" aria-hidden="true"></canvas>
      <div class="action-row">
        <p>Grabando… <span id="elapsed-time" class="mono-time">0:00</span></p>
        <button class="btn primary" id="stop-btn" type="button">■ Detener y analizar</button>
      </div>
    </div>
  `;
}

function analyzingView() {
  return `
    <div class="card" aria-busy="true">
      <p>Analizando tu grabación…</p>
    </div>
  `;
}

function resultView(result, audioUrl) {
  const { score, feedback, features } = result;
  const primaryMetrics = PRIMARY_FEATURES.map(
    (name) => `
      <div class="metric">
        <div class="metric-val">${Math.round(features[name])}</div>
        <div class="metric-lbl">${FEATURE_LABELS[name]}</div>
      </div>
    `,
  ).join("");

  const suggestions = feedback.suggestions
    .map((s) => `<li>${escapeHtml(s)}</li>`)
    .join("");

  return `
    <div class="card">
      ${renderScoreMeter(score)}
      <p>${escapeHtml(feedback.summary)}</p>
      <ul>${suggestions}</ul>
    </div>

    <div class="card">
      <p class="muted" style="margin-bottom:8px">Reproducir esta grabación</p>
      <audio controls src="${audioUrl}" class="playback-audio">
        Tu navegador no puede reproducir este audio aquí.
      </audio>
    </div>

    <h2>Desglose</h2>
    <div class="metrics-row">${primaryMetrics}</div>

    <details>
      <summary>Ver las 12 features completas</summary>
      ${renderFeatureBars(features)}
    </details>

    <div class="card action-row">
      <button class="btn primary" id="record-again-btn" type="button">Grabar de nuevo</button>
      <button class="btn" id="upload-btn" type="button">Subir otro archivo</button>
      <input type="file" id="upload-input" accept="audio/*" hidden />
    </div>
  `;
}

function errorView(message) {
  return `
    <div class="callout danger">
      <div class="callout-title">Algo no salió bien</div>
      <p>${escapeHtml(message)}</p>
    </div>
    <button class="btn primary" id="retry-btn" type="button">Intentar de nuevo</button>
  `;
}
