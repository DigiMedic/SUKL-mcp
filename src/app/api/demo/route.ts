import { readObject, isEmail, validConsent, createRateLimiter } from "@/lib/http-input";
import { NextRequest, NextResponse } from "next/server";
import { parseQuery } from "@/lib/demo-handler";
import {
  searchMedicines,
  getMedicineByCode,
  findPharmacies,
  getATCInfo,
  getMedicinesByATC,
} from "@/lib/sukl-client";

// ============================================================================
// Rate Limiting (in-memory, resets on cold start)
// ============================================================================

const checkRateLimit = createRateLimiter(10);

export async function POST(request: NextRequest) {
  // Rate limiting
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    "unknown";

  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Příliš mnoho požadavků. Zkuste to znovu za minutu." },
      { status: 429 }
    );
  }

  // Parse body
  let body: { query?: unknown };
  try {
    body = await readObject(request);
  } catch {
    return NextResponse.json(
      { error: "Neplatný formát požadavku." },
      { status: 400 }
    );
  }

  // Validate query
  const { query } = body;
  if (typeof query !== "string" || query.length < 2 || query.length > 200) {
    return NextResponse.json(
      { error: "Dotaz musí být text o délce 2–200 znaků." },
      { status: 400 }
    );
  }

  try {
    const parsed = parseQuery(query);
    const startTime = performance.now();

    switch (parsed.intent) {
      case "search": {
        const result = await searchMedicines(
          parsed.params.query as string,
          (parsed.params.limit as number) || 5
        );
        return NextResponse.json({
          type: "search",
          query: parsed.params.query,
          results: result.medicines,
          total: result.total_count,
          time_ms: Math.round(performance.now() - startTime),
        });
      }

      case "detail": {
        const medicine = await getMedicineByCode(
          parsed.params.sukl_code as string
        );
        return NextResponse.json({
          type: "detail",
          medicine,
          time_ms: Math.round(performance.now() - startTime),
        });
      }

      case "pharmacy": {
        const pharmacies = await findPharmacies(
          parsed.params.city as string | undefined
        );
        return NextResponse.json({
          type: "pharmacy",
          city: parsed.params.city || null,
          pharmacies: pharmacies.slice(0, 20),
          total: pharmacies.length,
          time_ms: Math.round(performance.now() - startTime),
        });
      }

      case "atc": {
        const atcCode = parsed.params.atc_code as string;
        const info = await getATCInfo(atcCode);
        const medicines = await getMedicinesByATC(atcCode);
        return NextResponse.json({
          type: "atc",
          info,
          medicines: medicines.slice(0, 10),
          medicines_total: medicines.length,
          time_ms: Math.round(performance.now() - startTime),
        });
      }

      default:
        return NextResponse.json(
          { error: "Neznámý typ dotazu." },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error("Demo API error:", error);
    return NextResponse.json(
      { error: "Interní chyba serveru." },
      { status: 500 }
    );
  }
}
