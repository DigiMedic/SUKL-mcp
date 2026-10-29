/**
 * Demo Chat Intent Parser
 * Pattern matching without LLM dependency
 */

export interface ParsedQuery {
  intent: "search" | "detail" | "pharmacy" | "atc";
  params: Record<string, string | boolean | number>;
}

// ATC code pattern: letter followed by digits, optionally more letter+digit groups
const ATC_PATTERN = /^(?:[A-Z]|[A-Z]\d{2}|[A-Z]\d{2}[A-Z]|[A-Z]\d{2}[A-Z]{2}|[A-Z]\d{2}[A-Z]{2}\d{2})$/i;

// 7-digit SÚKL code (with or without leading zeros)
const SUKL_CODE_PATTERN = /^\d{4,7}$/;

// Pharmacy keywords (Czech with/without diacritics)
const PHARMACY_KEYWORDS = [
  "lékárn",
  "lekarn",
  "pharmacy",
  "lékáren",
  "lékárna",
  "lekarna",
  "lekarny",
  "lékárny",
];

// City extraction from pharmacy queries
const PHARMACY_CITY_PATTERN =
  /(?:lékárn[\p{L}]*|lekarn[\p{L}]*|pharmacy)\s+(?:v|ve|na|blízko|poblíž|u|kolem)?\s*(.+)/iu;

export function parseQuery(input: string): ParsedQuery {
  const trimmed = input.trim();

  if (!trimmed) {
    return { intent: "search", params: { query: input, limit: 5 } };
  }

  // Check for SÚKL code (7-digit number)
  if (SUKL_CODE_PATTERN.test(trimmed)) {
    return {
      intent: "detail",
      params: { sukl_code: trimmed },
    };
  }

  // Check for ATC code — either explicit "ATC X..." prefix or matching pattern
  const atcPrefixMatch = trimmed.match(/^ATC\s+(.+)$/i);
  if (atcPrefixMatch) {
    return {
      intent: "atc",
      params: { atc_code: atcPrefixMatch[1].trim().toUpperCase() },
    };
  }

  if (ATC_PATTERN.test(trimmed)) {
    return {
      intent: "atc",
      params: { atc_code: trimmed.toUpperCase() },
    };
  }

  // Check for pharmacy intent
  const lowerInput = trimmed.toLowerCase();
  const isPharmacy = PHARMACY_KEYWORDS.some((kw) => lowerInput.includes(kw));

  if (isPharmacy) {
    const cityMatch = trimmed.match(PHARMACY_CITY_PATTERN);
    const city = cityMatch ? cityMatch[1].trim() : undefined;

    return {
      intent: "pharmacy",
      params: city ? { city } : {},
    };
  }

  // Default: search
  return {
    intent: "search",
    params: { query: trimmed, limit: 5 },
  };
}
