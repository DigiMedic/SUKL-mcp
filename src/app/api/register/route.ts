import { publicationPoliciesReady } from "@/lib/publication-config";
import { readObject, isEmail, validConsent, createRateLimiter } from "@/lib/http-input";
import { NextRequest, NextResponse } from "next/server";
import { createLead } from "@/lib/notion";
import { sendRegistrationConfirmation } from "@/lib/resend";

const VALID_USE_CASES = ["Chatbot", "Lékárna", "Klinický systém", "Výzkum", "Jiné"];
const checkRateLimit = createRateLimiter(5);

export async function POST(request: NextRequest) {
  if (process.env.NODE_ENV === "production" && (process.env.LEGACY_FORMS_ENABLED !== "true" || !publicationPoliciesReady())) return NextResponse.json({ error: "Webové formuláře nyní nejsou aktivní. Použijte stránku podpory." }, { status: 503 });
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

  const { email, company, useCase, name, useCaseDetail, gdprConsentAt } = body as {
    email?: string;
    company?: string;
    useCase?: string;
    name?: string;
    useCaseDetail?: string;
    gdprConsentAt?: string;
  };

  if (
    typeof name !== "string" ||
    name.trim().length < 2 ||
    name.length > 200
  ) {
    return NextResponse.json(
      { error: "Zadejte své jméno." },
      { status: 400 }
    );
  }

  if (
    !isEmail(email)
  ) {
    return NextResponse.json(
      { error: "Zadejte platný email." },
      { status: 400 }
    );
  }

  if (
    typeof company !== "string" ||
    company.trim().length < 2 ||
    company.length > 200
  ) {
    return NextResponse.json(
      { error: "Zadejte název firmy nebo projektu." },
      { status: 400 }
    );
  }

  if (!validConsent(gdprConsentAt)) {
    return NextResponse.json(
      { error: "Souhlas se zpracováním údajů je povinný." },
      { status: 400 }
    );
  }

  const selectedUseCase = VALID_USE_CASES.includes(useCase as string)
    ? (useCase as string)
    : "Jiné";

  const trimmedUseCaseDetail =
    typeof useCaseDetail === "string" ? useCaseDetail.trim().slice(0, 500) : undefined;

  try {
    await createLead({
      name: name.trim(),
      email: email.trim(),
      company: company.trim(),
      useCase: selectedUseCase,
      useCaseDetail: trimmedUseCaseDetail || undefined,
      gdprConsentAt: new Date().toISOString(),
    });

    // Send confirmation email (non-blocking)
    try {
      await sendRegistrationConfirmation(email.trim(), name.trim());
    } catch (emailError) {
      console.error("Resend email delivery failed.");
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Form submission failed.");
    return NextResponse.json(
      { error: "Nepodařilo se odeslat registraci. Zkuste to znovu." },
      { status: 500 }
    );
  }
}
