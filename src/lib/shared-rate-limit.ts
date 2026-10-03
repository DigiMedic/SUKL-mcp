import { createHmac } from "node:crypto";
import { createRateLimiter } from "./http-input";
const local = createRateLimiter(100);
export function sharedRateLimitConfigured() {
  return Boolean(process.env.RATE_LIMIT_REDIS_REST_URL && process.env.RATE_LIMIT_REDIS_REST_TOKEN && process.env.RATE_LIMIT_HASH_SECRET);
}
export async function allowMcpRequest(ip: string): Promise<boolean> {
  if (!sharedRateLimitConfigured()) {
    if (process.env.PUBLIC_LAUNCH_MODE === "true") throw new Error("Shared rate limit is required for public launch.");
    return local(ip);
  }
  const base = process.env.RATE_LIMIT_REDIS_REST_URL!;
  if (new URL(base).protocol !== "https:") throw new Error("Invalid rate limit service.");
  const digest = createHmac("sha256",process.env.RATE_LIMIT_HASH_SECRET!).update(ip).digest("hex");
  const key = `sukl:mcp:${Math.floor(Date.now()/60_000)}:${digest}`;
  const response = await fetch(base,{method:"POST",headers:{Authorization:`Bearer ${process.env.RATE_LIMIT_REDIS_REST_TOKEN}`,"Content-Type":"application/json"},body:JSON.stringify(["EVAL","local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",1,key]),signal:AbortSignal.timeout(5000),cache:"no-store"});
  if (!response.ok) throw new Error("Rate limit service unavailable.");
  const body = await response.json();
  if (body.error || !Number.isInteger(body.result) || body.result < 1) throw new Error("Invalid rate limit response.");
  return body.result <= 100;
}
