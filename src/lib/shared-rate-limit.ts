import { createHmac } from "node:crypto";
import { createRateLimiter } from "./http-input";
const local = createRateLimiter(100);
function redisConfig() {
  // Select a complete pair; never combine credentials from two databases.
  const customUrl = process.env.RATE_LIMIT_REDIS_REST_URL;
  const customToken = process.env.RATE_LIMIT_REDIS_REST_TOKEN;
  const url = customUrl || customToken ? customUrl : process.env.UPSTASH_REDIS_REST_URL;
  const token = customUrl || customToken ? customToken : process.env.UPSTASH_REDIS_REST_TOKEN;
  const salt = process.env.RATE_LIMIT_HASH_SECRET;
  if (!url || !token?.trim() || !salt || salt.trim().length < 32 || /[\r\n]/.test(token)) return null;
  try {
    const endpoint = new URL(url);
    if (endpoint.protocol !== "https:" || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) return null;
  } catch { return null; }
  return {url,token,salt};
}
export function sharedRateLimitConfigured() {
  return Boolean(redisConfig());
}
export async function allowMcpRequest(ip: string): Promise<boolean> {
  const config = redisConfig();
  if (!config) {
    const hasCredentials = Boolean(process.env.RATE_LIMIT_REDIS_REST_URL || process.env.RATE_LIMIT_REDIS_REST_TOKEN || process.env.UPSTASH_REDIS_REST_URL || process.env.UPSTASH_REDIS_REST_TOKEN);
    if (process.env.PUBLIC_LAUNCH_MODE === "true" || hasCredentials) throw new Error("Valid shared rate limit configuration is required.");
    return local(ip);
  }
  const digest = createHmac("sha256",config.salt).update(ip).digest("hex");
  const key = `sukl:mcp:${Math.floor(Date.now()/60_000)}:${digest}`;
  const response = await fetch(config.url,{method:"POST",headers:{Authorization:`Bearer ${config.token}`,"Content-Type":"application/json"},body:JSON.stringify(["EVAL","local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",1,key]),signal:AbortSignal.timeout(5000),cache:"no-store"});
  if (!response.ok) throw new Error("Rate limit service unavailable.");
  const body = await response.json();
  if (body.error || !Number.isInteger(body.result) || body.result < 1) throw new Error("Invalid rate limit response.");
  return body.result <= 100;
}
