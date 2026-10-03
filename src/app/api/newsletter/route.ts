import { acquireNewsletterLock } from "@/lib/newsletter-lock";
import { readObject, isEmail, validConsent, createRateLimiter } from "@/lib/http-input";
import { NextRequest, NextResponse } from "next/server";
import { createNewsletterSubscriber, checkNewsletterDuplicate } from "@/lib/notion";
import { sendNewsletterConfirmation } from "@/lib/resend";

const checkRateLimit = createRateLimiter(5);

export async function POST(request: NextRequest) {
  if (process.env.NODE_ENV === "production" && (process.env.LEGACY_FORMS_ENABLED !== "true" || process.env.PUBLICATION_POLICY_CONFIRMED !== "true")) return NextResponse.json({ error: "Webové formuláře nyní nejsou aktivní. Použijte stránku podpory." }, { status: 503 });
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    "unknown";

  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Příliš mnoho požadavků. Zkuste to za minutu." },
      { status: 429 }
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await readObject(request);
  } catch {
    return NextResponse.json(
      { error: "Neplatný formát požadavku." },
      { status: 400 }
    );
  }

  const { email, gdprConsentAt } = body as {
    email?: string;
    gdprConsentAt?: string;
  };

  if (
    !isEmail(email)
  ) {
    return NextResponse.json(
      { error: "Zadejte platný email." },
      { status: 400 }
    );
  }

  if (!validConsent(gdprConsentAt)) {
    return NextResponse.json(
      { error: "Souhlas se zpracováním údajů je povinný." },
      { status: 400 }
    );
  }

  const trimmedEmail = email.trim().toLowerCase();
  let release: () => Promise<void>;
  try { release = await acquireNewsletterLock(trimmedEmail); } catch { return NextResponse.json({ error: "Odběr nyní nelze bezpečně zpracovat. Zkuste to později." }, { status: 503 }); }
  try {

  let isDuplicate: boolean;
  try { isDuplicate = await checkNewsletterDuplicate(trimmedEmail); } catch { return NextResponse.json({ error: "Odběr nyní nelze ověřit. Zkuste to později." }, { status: 503 }); }
  if (isDuplicate) {
    return NextResponse.json({
      success: true,
      message: "Tento email je již přihlášen k odběru.",
    });
  }

  try {
    await createNewsletterSubscriber(trimmedEmail, new Date().toISOString());

    // Send confirmation email (non-blocking)
    try {
      await sendNewsletterConfirmation(trimmedEmail);
    } catch (emailError) {
      console.error("Resend email delivery failed.");
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Form submission failed.");
    return NextResponse.json(
      { error: "Nepodařilo se přihlásit k odběru. Zkuste to znovu." },
      { status: 500 }
    );
  }
  } finally { await release().catch(() => { console.error("Newsletter lease cleanup failed; lease expires automatically."); }); }
}
