import { readObject, isEmail, validConsent, createRateLimiter } from "@/lib/http-input";
import { NextRequest, NextResponse } from "next/server";
import { createEnterpriseContact } from "@/lib/notion";
import { sendEnterpriseNotification } from "@/lib/resend";

const VALID_SIZES = ["1–10", "11–50", "51–200", "200+"];
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

  const { email, company, phone, companySize, message, name, gdprConsentAt } = body as {
    email?: string;
    company?: string;
    phone?: string;
    companySize?: string;
    message?: string;
    name?: string;
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
      { error: "Zadejte název firmy." },
      { status: 400 }
    );
  }

  if (
    typeof message !== "string" ||
    message.trim().length < 10 ||
    message.length > 2000
  ) {
    return NextResponse.json(
      { error: "Zpráva musí mít alespoň 10 znaků." },
      { status: 400 }
    );
  }

  if (!validConsent(gdprConsentAt)) {
    return NextResponse.json(
      { error: "Souhlas se zpracováním údajů je povinný." },
      { status: 400 }
    );
  }

  if (phone !== undefined && (typeof phone !== "string" || phone.length > 40)) return NextResponse.json({ error: "Neplatné telefonní číslo." }, { status: 400 });

  const selectedSize = VALID_SIZES.includes(companySize as string)
    ? (companySize as string)
    : "1–10";

  try {
    await createEnterpriseContact({
      name: name.trim(),
      email: email.trim(),
      company: company.trim(),
      phone: typeof phone === "string" ? phone.trim() : undefined,
      companySize: selectedSize,
      message: message.trim(),
      gdprConsentAt: new Date().toISOString(),
    });

    // Send notification email (non-blocking)
    try {
      await sendEnterpriseNotification({
        name: name.trim(),
        email: email.trim(),
        company: company.trim(),
        companySize: selectedSize,
        message: message.trim(),
      });
    } catch (emailError) {
      console.error("Resend email delivery failed.");
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Form submission failed.");
    return NextResponse.json(
      { error: "Nepodařilo se odeslat poptávku. Zkuste to znovu." },
      { status: 500 }
    );
  }
}
