/**
 * Captura audio del micrófono y lo transmite al backend por WebSocket para
 * el modo en vivo (ver docs/API.md, WS /api/v1/stream).
 *
 * Usa ScriptProcessorNode, no AudioWorkletNode: está deprecado pero sigue
 * funcionando en todos los navegadores actuales, y no necesita cargar un
 * archivo de worklet aparte. Si esto da problemas reales, migrar a
 * AudioWorkletNode es el reemplazo correcto.
 */
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:9001";
const BUFFER_SIZE = 4096;

export class LiveStreamError extends Error {
  constructor(message) {
    super(message);
    this.name = "LiveStreamError";
  }
}

function floatTo16BitPCM(floatData) {
  const pcm16 = new Int16Array(floatData.length);
  for (let i = 0; i < floatData.length; i++) {
    const s = Math.max(-1, Math.min(1, floatData[i]));
    pcm16[i] = s < 0 ? s * 32768 : s * 32767;
  }
  return pcm16;
}

/**
 * Empieza a capturar y transmitir. onUpdate(data) se llama con cada
 * score_update ({score, score_smoothed, features}). Regresa una función de
 * limpieza que corta el micrófono y cierra la conexión.
 */
export async function startLiveStream({ onUpdate, onError }) {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    throw new LiveStreamError(
      "No pudimos acceder al micrófono para el modo en vivo. Revisa los permisos del navegador.",
    );
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const audioContext = new AudioContextClass();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);
  // Un GainNode en 0 en vez de conectar processor directo a destination:
  // ScriptProcessorNode necesita estar conectado a algo para que
  // onaudioprocess dispare en todos los navegadores, pero conectarlo
  // directo a destination haría audible (eco) el propio micrófono.
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;

  const ws = new WebSocket(`${WS_BASE}/api/v1/stream`);
  ws.binaryType = "arraybuffer";

  function cleanup() {
    processor.onaudioprocess = null;
    processor.disconnect();
    source.disconnect();
    silentGain.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    audioContext.close().catch(() => {});
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  }

  try {
    await new Promise((resolve, reject) => {
      ws.addEventListener("open", () => {
        ws.send(JSON.stringify({ sample_rate: audioContext.sampleRate }));
        resolve();
      });
      ws.addEventListener(
        "error",
        () => reject(new LiveStreamError("No pudimos conectar con el servidor para el modo en vivo.")),
        { once: true },
      );
    });
  } catch (err) {
    cleanup();
    throw err;
  }

  ws.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "score_update") onUpdate(data);
    } catch {
      // ignora mensajes que no se puedan interpretar
    }
  });
  ws.addEventListener("close", (event) => {
    if (!event.wasClean) onError?.(new LiveStreamError("Se perdió la conexión del modo en vivo."));
  });

  processor.onaudioprocess = (event) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    const pcm16 = floatTo16BitPCM(event.inputBuffer.getChannelData(0));
    ws.send(pcm16.buffer);
  };

  source.connect(processor);
  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  return cleanup;
}
