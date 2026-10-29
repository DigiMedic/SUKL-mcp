import { describe, it, expect, vi, afterEach } from "vitest";
const { send } = vi.hoisted(() => ({ send:vi.fn() }));
vi.mock("resend", () => ({ Resend:class { emails = {send}; } }));
vi.mock("@/lib/notion", () => ({createLead:vi.fn(),createEnterpriseContact:vi.fn()}));
import { POST as register } from "@/app/api/register/route";
import { POST as contact } from "@/app/api/contact/route";
import { POST as demo } from "@/app/api/demo/route";
import { NextRequest } from "next/server";
import { allowMcpRequest } from "@/lib/shared-rate-limit";
import { acquireNewsletterLock } from "@/lib/newsletter-lock";
import { readObject, validConsent } from "@/lib/http-input";
import { escapeEmailHtml, sendNewsletterConfirmation } from "@/lib/resend";

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.clearAllMocks(); });
const request = (body:unknown) => new NextRequest("http://localhost/api/form",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
describe("Input, email and shared service boundaries", () => {
  it("rejects null or array form bodies without writes or internal errors", async () => {
    for (const route of [register,contact,demo]) for (const body of [null,[]]) expect((await route(request(body))).status).toBe(400);
  });
  it("rejects arbitrary or future consent dates and limits streamed input", async () => {
    expect(validConsent("yes")).toBe(false); expect(validConsent("2099-01-01T00:00:00Z")).toBe(false);
    await expect(readObject(request({query:"x".repeat(17000)}))).rejects.toMatchObject({status:413});
    await expect(readObject(request(null))).rejects.toMatchObject({status:400});
  });
  it("escapes untrusted email HTML and handles provider error objects", async () => {
    expect(escapeEmailHtml('<a href="x">A & B</a>')).toBe("&lt;a href=&quot;x&quot;&gt;A &amp; B&lt;/a&gt;");
    vi.stubEnv("RESEND_API_KEY","synthetic-test-key"); send.mockResolvedValue({data:null,error:{message:"rejected"}});
    await expect(sendNewsletterConfirmation("test@example.com")).rejects.toThrow("rejected");
  });
  it("fails closed at public launch without a shared limiter", async () => {
    vi.stubEnv("PUBLIC_LAUNCH_MODE","true"); vi.stubEnv("RATE_LIMIT_REDIS_REST_URL","");
    await expect(allowMcpRequest("203.0.113.1")).rejects.toThrow();
  });
  it("uses one atomic expiring counter, pseudonymises IP and rejects a backend outage", async () => {
    vi.stubEnv("RATE_LIMIT_REDIS_REST_URL","https://redis.example.test"); vi.stubEnv("RATE_LIMIT_REDIS_REST_TOKEN","synthetic-token"); vi.stubEnv("RATE_LIMIT_HASH_SECRET","synthetic-salt-at-least-32-characters");
    const f = vi.fn().mockResolvedValueOnce(Response.json({result:100})).mockResolvedValueOnce(Response.json({result:101})).mockResolvedValueOnce(new Response(null,{status:503})); vi.stubGlobal("fetch",f);
    expect(await allowMcpRequest("203.0.113.1")).toBe(true); expect(await allowMcpRequest("203.0.113.1")).toBe(false);
    expect(f.mock.calls[0][1].body).not.toContain("203.0.113.1"); expect(f.mock.calls[0][1].body).toContain("EXPIRE");
    await expect(allowMcpRequest("203.0.113.1")).rejects.toThrow();
  });
  it("uses an atomic shared newsletter lease and deletes only the owning token", async () => {
    vi.stubEnv("NEWSLETTER_REDIS_REST_URL","https://redis.example.test"); vi.stubEnv("NEWSLETTER_REDIS_REST_TOKEN","synthetic-token");
    const f = vi.fn().mockResolvedValueOnce(Response.json({result:"OK"})).mockResolvedValueOnce(Response.json({result:1})).mockResolvedValueOnce(Response.json({result:null})); vi.stubGlobal("fetch",f);
    const release = await acquireNewsletterLock("TEST@example.com");
    const command = JSON.parse(f.mock.calls[0][1].body); expect(command[0]).toBe("SET"); expect(command).toContain("NX"); expect(command).toContain(120); expect(command[1]).not.toContain("TEST@example.com");
    await release(); expect(JSON.parse(f.mock.calls[1][1].body)[1]).toContain("ARGV[1]");
    await expect(acquireNewsletterLock("TEST@example.com")).rejects.toThrow();
  });
});
