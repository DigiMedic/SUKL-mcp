export class HttpInputError extends Error {
  constructor(message: string, public status = 400, public rpcCode = -32600) { super(message); }
}
export async function readObject(request: Request): Promise<Record<string, unknown>> {
  const reader = request.body?.getReader();
  if (!reader) throw new HttpInputError("Prázdný požadavek.");
  const chunks: Uint8Array[] = []; let size = 0;
  try {
    while (true) { const { done, value } = await reader.read(); if (done) break; size += value.byteLength; if (size > 16_384) { await reader.cancel(); throw new HttpInputError("Příliš velký požadavek.", 413); } chunks.push(value); }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  let body: unknown;
  try { body = JSON.parse(new TextDecoder().decode(bytes)); } catch { throw new HttpInputError("Neplatný JSON.", 400, -32700); }
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new HttpInputError("Očekáván jeden objekt požadavku; dávky nejsou podporovány.");
  return body as Record<string, unknown>;
}
export function isEmail(value: unknown): value is string {
  return typeof value === "string" && value.length <= 200 && /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(value.trim());
}
export function validConsent(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value)) && Date.parse(value) <= Date.now() + 60_000;
}
/** Best effort process-local limiter. Configure a shared edge limit before public launch. */
export function createRateLimiter(limit: number) {
  const entries = new Map<string, { count: number; resetAt: number }>();
  return (key: string) => {
    const now = Date.now();
    for (const [ip, entry] of entries) if (entry.resetAt <= now) entries.delete(ip);
    const entry = entries.get(key);
    if (!entry) { if (entries.size >= 10_000) return false; entries.set(key, { count: 1, resetAt: now + 60_000 }); return true; }
    if (entry.count >= limit) return false; entry.count++; return true;
  };
}
