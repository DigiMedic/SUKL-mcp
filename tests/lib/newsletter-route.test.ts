vi.mock("@/lib/newsletter-lock", () => ({ acquireNewsletterLock: vi.fn().mockResolvedValue(async () => {}) }));
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock Notion client
vi.mock("@/lib/notion", () => ({
  createNewsletterSubscriber: vi.fn().mockResolvedValue({}),
  checkNewsletterDuplicate: vi.fn().mockResolvedValue(false),
}));

// Mock Resend
vi.mock("@/lib/resend", () => ({
  sendNewsletterConfirmation: vi.fn().mockResolvedValue({}),
}));

import { POST } from "@/app/api/newsletter/route";
import { createNewsletterSubscriber, checkNewsletterDuplicate } from "@/lib/notion";
import { sendNewsletterConfirmation } from "@/lib/resend";
import { NextRequest } from "next/server";

let ipCounter = 0;

function makeRequest(body: Record<string, unknown>): NextRequest {
  ipCounter++;
  return new NextRequest("http://localhost:3000/api/newsletter", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-forwarded-for": `10.0.0.${ipCounter}`,
    },
    body: JSON.stringify(body),
  });
}

describe("POST /api/newsletter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates subscriber with valid email and GDPR consent", async () => {
    const req = makeRequest({
      email: "jan@firma.cz",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.success).toBe(true);
    expect(createNewsletterSubscriber).toHaveBeenCalledWith(
      "jan@firma.cz",
      expect.any(String)
    );
    expect(Date.parse(vi.mocked(createNewsletterSubscriber).mock.calls[0][1])).toBeGreaterThan(Date.now() - 1000);
  });

  it("returns 400 for missing email", async () => {
    const req = makeRequest({
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data.error).toBe("Zadejte platný email.");
  });

  it("returns 400 for invalid email", async () => {
    const req = makeRequest({
      email: "not-an-email",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data.error).toBe("Zadejte platný email.");
  });

  it("returns 400 for missing GDPR consent", async () => {
    const req = makeRequest({
      email: "jan@firma.cz",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data.error).toBe("Souhlas se zpracováním údajů je povinný.");
  });

  it("returns success with message for duplicate email", async () => {
    vi.mocked(checkNewsletterDuplicate).mockResolvedValueOnce(true);

    const req = makeRequest({
      email: "jan@firma.cz",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.message).toBe("Tento email je již přihlášen k odběru.");
    expect(createNewsletterSubscriber).not.toHaveBeenCalled();
  });

  it("succeeds even when Resend fails", async () => {
    vi.mocked(sendNewsletterConfirmation).mockRejectedValueOnce(new Error("Resend down"));

    const req = makeRequest({
      email: "jan@firma.cz",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.success).toBe(true);
    expect(createNewsletterSubscriber).toHaveBeenCalled();
  });

  it("sends confirmation email on success", async () => {
    const req = makeRequest({
      email: "jan@firma.cz",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    await POST(req);

    expect(sendNewsletterConfirmation).toHaveBeenCalledWith("jan@firma.cz");
  });

  it("proceeds when duplicate check fails", async () => {
    // checkNewsletterDuplicate returns false on error (per spec)
    vi.mocked(checkNewsletterDuplicate).mockResolvedValueOnce(false);

    const req = makeRequest({
      email: "jan@firma.cz",
      gdprConsentAt: "2026-03-17T14:00:00.000Z",
    });

    const res = await POST(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.success).toBe(true);
    expect(createNewsletterSubscriber).toHaveBeenCalled();
  });
});
