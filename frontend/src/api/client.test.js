import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalyzeError, analyzeAudio } from "./client.js";

function mockFetchOnce({ ok, status, json }) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => json,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("analyzeAudio", () => {
  it("returns the parsed JSON on a successful response", async () => {
    mockFetchOnce({ ok: true, status: 200, json: { score: 42 } });
    const result = await analyzeAudio(new Blob(["fake"]), "voz.webm");
    expect(result).toEqual({ score: 42 });
  });

  it("relays the backend's own detail message on 422 (voz insuficiente o tono inestable)", async () => {
    mockFetchOnce({
      ok: false,
      status: 422,
      json: { detail: "La grabación mezcla dos tonos de voz muy distintos." },
    });
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toMatchObject({
      message: "La grabación mezcla dos tonos de voz muy distintos.",
      status: 422,
    });
  });

  it("falls back to a generic message on 422 if the backend sent no detail", async () => {
    mockFetchOnce({ ok: false, status: 422, json: {} });
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toThrow(
      "No pudimos analizar esa grabación. Intenta de nuevo.",
    );
  });

  it("shows a friendly message on 400 (archivo inválido)", async () => {
    mockFetchOnce({ ok: false, status: 400, json: {} });
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toMatchObject({ status: 400 });
  });

  it("shows a connection message when fetch itself fails (sin red)", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("network error"));
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining("conectar"),
    });
  });

  it("shows a generic message for an unexpected server error", async () => {
    mockFetchOnce({ ok: false, status: 500, json: {} });
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toMatchObject({ status: 500 });
  });

  it("rejects with an AnalyzeError instance in every failure case", async () => {
    mockFetchOnce({ ok: false, status: 422, json: { detail: "x" } });
    await expect(analyzeAudio(new Blob(["fake"]))).rejects.toBeInstanceOf(AnalyzeError);
  });
});
