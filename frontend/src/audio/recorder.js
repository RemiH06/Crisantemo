/**
 * Envoltura delgada sobre MediaRecorder para grabar desde el micrófono.
 * No hace VAD ni indicador de calidad de audio (eso es Fase 4-5); esto solo
 * graba y entrega un Blob.
 */
export class MicrophoneError extends Error {
  constructor(message) {
    super(message);
    this.name = "MicrophoneError";
  }
}

function friendlyPermissionMessage(err) {
  if (err && err.name === "NotAllowedError") {
    return "No tenemos permiso para usar tu micrófono. Puedes darlo desde el ícono de candado/cámara del navegador, o subir un archivo de audio en su lugar.";
  }
  if (err && err.name === "NotFoundError") {
    return "No encontramos un micrófono disponible. Puedes subir un archivo de audio en su lugar.";
  }
  return "No pudimos acceder al micrófono. Puedes subir un archivo de audio en su lugar.";
}

/**
 * Pide permiso de micrófono y regresa un controlador { start, stop }.
 * stop() resuelve con el Blob grabado. Lanza MicrophoneError si no se pudo
 * obtener acceso al micrófono.
 */
export async function createRecorder() {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    throw new MicrophoneError(friendlyPermissionMessage(err));
  }

  const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks = [];
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });

  return {
    stream,
    start() {
      chunks.length = 0;
      recorder.start();
    },
    stop() {
      return new Promise((resolve) => {
        recorder.addEventListener(
          "stop",
          () => {
            stream.getTracks().forEach((track) => track.stop());
            resolve(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
          },
          { once: true },
        );
        recorder.stop();
      });
    },
  };
}
