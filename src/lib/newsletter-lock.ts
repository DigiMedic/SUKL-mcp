import { createHash, randomUUID } from "node:crypto";
/** Shared lease prevents a check/create race across serverless instances. */
export async function acquireNewsletterLock(email: string): Promise<() => Promise<void>> {
  const base = process.env.NEWSLETTER_REDIS_REST_URL;
  const token = process.env.NEWSLETTER_REDIS_REST_TOKEN;
  if (!base || !token || new URL(base).protocol !== "https:") throw new Error("Shared newsletter lock is not configured.");
  const key = `sukl:newsletter:${createHash("sha256").update(email.toLowerCase()).digest("hex")}`;
  const owner = randomUUID();
  async function command(values: (string | number)[]) {
    const res = await fetch(base!, { method:"POST", headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"}, body:JSON.stringify(values), signal:AbortSignal.timeout(8000), cache:"no-store" });
    if (!res.ok) throw new Error("Shared newsletter lock is unavailable.");
    const result = await res.json();
    if (result.error) throw new Error("Shared newsletter lock command failed.");
    return result.result;
  }
  if (await command(["SET",key,owner,"NX","EX",120]) !== "OK") throw new Error("Newsletter request already in progress.");
  return async () => {
    // Delete only our own lease; never remove a later request's lock.
    await command(["EVAL","if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",1,key,owner]);
  };
}
