/**
 * Cliente del backend de análisis. Ver docs/API.md para el contrato de
 * POST /api/v1/analyze.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:9001";

export class AnalyzeError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "AnalyzeError";
    this.status = status;
  }
}

/**
 * Sube un audio (Blob) al backend y regresa el análisis completo.
 * Lanza AnalyzeError con un mensaje ya pensado para mostrarse tal cual.
 */
export async function analyzeAudio(blob, filename = "grabacion.webm") {
  const form = new FormData();
  form.append("file", blob, filename);

  let response;
  try {
    response = await fetch(`${API_BASE}/api/v1/analyze`, { method: "POST", body: form });
  } catch {
    throw new AnalyzeError(
      "No pudimos conectar con el servidor. Revisa tu conexión e intenta de nuevo.",
      0,
    );
  }

  if (!response.ok) {
    if (response.status === 422) {
      // El backend ya redacta este mensaje en tono de apoyo (ver
      // shared/acoustic_features/features.py), así que se muestra tal cual
      // en vez de una versión genérica fija aquí que no distinguiría entre
      // "grabación muy corta" y "la grabación mezcla dos tonos distintos".
      const body = await response.json().catch(() => ({}));
      throw new AnalyzeError(
        body.detail || "No pudimos analizar esa grabación. Intenta de nuevo.",
        response.status,
      );
    }
    if (response.status === 400) {
      throw new AnalyzeError(
        "Ese archivo no se pudo leer como audio. Prueba grabando de nuevo o con otro archivo.",
        response.status,
      );
    }
    throw new AnalyzeError("Algo falló de nuestro lado, intenta de nuevo en un momento.", response.status);
  }

  return response.json();
}
