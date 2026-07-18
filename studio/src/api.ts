const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export async function getVoices(model: string, signal?: AbortSignal): Promise<string[]> {
  const response = await fetch(
    `${API_BASE}/v1/audio/voices?model=${encodeURIComponent(model)}`,
    { signal },
  );

  if (!response.ok) throw new Error(await readError(response));
  const data = (await response.json()) as { voices?: string[] };
  return data.voices ?? [];
}

export async function createSpeech(input: string, model: string, voice: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/v1/audio/speech`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input, model, voice }),
  });

  if (!response.ok) throw new Error(await readError(response));
  return response.blob();
}

export async function streamSpeech(
  input: string,
  model: string,
  voice: string,
  onChunk: (chunk: ArrayBuffer) => Promise<void>,
): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/audio/speech/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input, model, voice }),
  });

  if (!response.ok) throw new Error(await readError(response));
  if (!response.body) throw new Error("Streaming is not supported by this browser.");

  const reader = response.body.getReader();
  let pending = new Uint8Array(0);
  let frameLength: number | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const merged = new Uint8Array(pending.length + value.length);
    merged.set(pending);
    merged.set(value, pending.length);
    pending = merged;

    while (true) {
      if (frameLength === null) {
        if (pending.length < 4) break;
        frameLength = new DataView(pending.buffer, pending.byteOffset, 4).getUint32(0);
        pending = pending.slice(4);
      }
      if (pending.length < frameLength) break;
      const frame = pending.slice(0, frameLength).buffer;
      pending = pending.slice(frameLength);
      frameLength = null;
      await onChunk(frame);
    }
  }

  if (frameLength !== null || pending.length) throw new Error("The audio stream ended unexpectedly.");
}

async function readError(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}
