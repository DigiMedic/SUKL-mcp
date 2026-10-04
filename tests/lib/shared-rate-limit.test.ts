import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { allowMcpRequest, sharedRateLimitConfigured } from "@/lib/shared-rate-limit";

beforeEach(() => {
  for (const key of ["RATE_LIMIT_REDIS_REST_URL","RATE_LIMIT_REDIS_REST_TOKEN","UPSTASH_REDIS_REST_URL","UPSTASH_REDIS_REST_TOKEN","RATE_LIMIT_HASH_SECRET"]) vi.stubEnv(key,"");
  vi.stubEnv("PUBLIC_LAUNCH_MODE","true");
  vi.stubEnv("RATE_LIMIT_HASH_SECRET","synthetic-test-salt-at-least-32-characters");
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

it("uses the credentials injected by the Vercel Upstash integration", async () => {
  vi.stubEnv("UPSTASH_REDIS_REST_URL","https://upstash.example.test");
  vi.stubEnv("UPSTASH_REDIS_REST_TOKEN","synthetic-upstash-token");
  const fetcher = vi.fn().mockResolvedValue(Response.json({result:1})); vi.stubGlobal("fetch",fetcher);
  expect(sharedRateLimitConfigured()).toBe(true);
  expect(await allowMcpRequest("203.0.113.9")).toBe(true);
  expect(fetcher.mock.calls[0][0]).toBe("https://upstash.example.test");
  expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer synthetic-upstash-token");
  expect(fetcher.mock.calls[0][1].body).not.toContain("203.0.113.9");
});

it("prefers a complete custom pair and never mixes providers", async () => {
  vi.stubEnv("UPSTASH_REDIS_REST_URL","https://upstash.example.test");
  vi.stubEnv("UPSTASH_REDIS_REST_TOKEN","synthetic-upstash-token");
  vi.stubEnv("RATE_LIMIT_REDIS_REST_URL","https://custom.example.test");
  vi.stubEnv("RATE_LIMIT_REDIS_REST_TOKEN","synthetic-custom-token");
  const fetcher = vi.fn().mockResolvedValue(Response.json({result:1})); vi.stubGlobal("fetch",fetcher);
  await allowMcpRequest("203.0.113.9");
  expect(fetcher.mock.calls[0][0]).toBe("https://custom.example.test");
  expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer synthetic-custom-token");
  vi.stubEnv("RATE_LIMIT_REDIS_REST_TOKEN","");
  expect(sharedRateLimitConfigured()).toBe(false);
  await expect(allowMcpRequest("203.0.113.9")).rejects.toThrow();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it.each(["http://redis.example.test","https://user:password@redis.example.test","https://redis.example.test?token=secret","https://redis.example.test#fragment","invalid-url"])("rejects an unsafe endpoint before sending credentials: %s", async url => {
  vi.stubEnv("UPSTASH_REDIS_REST_URL",url); vi.stubEnv("UPSTASH_REDIS_REST_TOKEN","synthetic-token");
  const fetcher = vi.fn(); vi.stubGlobal("fetch",fetcher);
  expect(sharedRateLimitConfigured()).toBe(false);
  await expect(allowMcpRequest("203.0.113.9")).rejects.toThrow();
  expect(fetcher).not.toHaveBeenCalled();
});

it("does not report a weak salt or incomplete credentials as ready, even before launch", async () => {
  vi.stubEnv("PUBLIC_LAUNCH_MODE","false");
  vi.stubEnv("UPSTASH_REDIS_REST_URL","https://upstash.example.test");
  vi.stubEnv("UPSTASH_REDIS_REST_TOKEN","synthetic-token");
  for (const salt of ["short", " ".repeat(40)]) {
    vi.stubEnv("RATE_LIMIT_HASH_SECRET",salt);
    expect(sharedRateLimitConfigured()).toBe(false);
    await expect(allowMcpRequest("203.0.113.9")).rejects.toThrow();
  }
  vi.stubEnv("RATE_LIMIT_HASH_SECRET","synthetic-test-salt-at-least-32-characters");
  vi.stubEnv("UPSTASH_REDIS_REST_TOKEN","");
  expect(sharedRateLimitConfigured()).toBe(false);
  await expect(allowMcpRequest("203.0.113.9")).rejects.toThrow();
});
