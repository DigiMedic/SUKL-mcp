import { getATCInfo, getCatalogueProvenance, getMedicineByCode, getMedicinesByATC, searchMedicines } from "./sukl-client";
import type { MedicineBasic } from "./types";

export class CatalogueInputError extends Error {}
export class CatalogueUpstreamError extends Error {}

export function catalogueCode(value: unknown): string {
  if (typeof value !== "string" || !/^\d{1,7}$/.test(value)) {
    throw new CatalogueInputError("Kód SÚKL musí být řetězec s 1 až 7 číslicemi.");
  }
  return value.padStart(7, "0");
}

function text(value: unknown, name: string, max: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > max) {
    throw new CatalogueInputError(`${name}: očekáván neprázdný text do ${max} znaků.`);
  }
  return value.trim();
}

function limit(value: unknown): number {
  if (value === undefined) return 10;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 20) {
    throw new CatalogueInputError("limit musí být celé číslo od 1 do 20.");
  }
  return value;
}

export function catalogueMedicine(m: MedicineBasic) {
  return {
    sukl_code: catalogueCode(m.sukl_code), name: m.name, strength: m.strength,
    form: m.form, package: m.package, atc_code: m.atc_code,
    reported_substance: m.substance,
    source_url: "https://prehledy.sukl.cz/prehled_leciv.html",
  };
}

// Each operation validates the same narrow arguments advertised in its schema.
export async function catalogueOperation(name: string, args: Record<string, unknown>) {
  const provenance = getCatalogueProvenance();
  switch (name) {
    case "search_medicines": {
      const query = text(args.query, "query", 100);
      const result = await searchMedicines(query, limit(args.limit));
      return { status: result.total_count ? "ok" : "no_match", medicines: result.medicines.map(catalogueMedicine), total_count: result.total_count, provenance };
    }
    case "get_medicine": {
      const code = catalogueCode(args.sukl_code);
      const medicine = await getMedicineByCode(code);
      return { status: medicine ? "ok" : "not_found", medicine: medicine ? { ...catalogueMedicine(medicine), dispensing_code: medicine.dispensing, registration_status_code: medicine.registration_status } : null, provenance };
    }
    case "get_atc_group": {
      const code = text(args.atc_code, "atc_code", 7).toUpperCase();
      if (!/^(?:[A-Z]|[A-Z]\d{2}|[A-Z]\d{2}[A-Z]|[A-Z]\d{2}[A-Z]{2}|[A-Z]\d{2}[A-Z]{2}\d{2})$/.test(code)) {
        throw new CatalogueInputError("Neplatný kód ATC.");
      }
      const info = await getATCInfo(code);
      const medicines = info ? await getMedicinesByATC(code) : [];
      return { status: info ? "ok" : "not_found", atc: info, medicines: medicines.slice(0, limit(args.limit)).map(catalogueMedicine), total_count: medicines.length, provenance };
    }
    case "get_medicine_document": {
      const code = catalogueCode(args.sukl_code);
      if (args.document_type !== "PIL" && args.document_type !== "SPC") {
        throw new CatalogueInputError("document_type musí být PIL nebo SPC.");
      }
      const medicine = await getMedicineByCode(code);
      if (!medicine) return { status: "not_found", document: null, provenance };
      const response = await fetch(`https://prehledy.sukl.cz/dlp/v1/dokumenty-metadata/${code}`, { signal: AbortSignal.timeout(8000), cache: "no-store" });
      if (!response.ok) throw new CatalogueUpstreamError("SÚKL nyní neposkytl metadata dokumentů. Zkuste požadavek později.");
      const docs: unknown = await response.json();
      if (!Array.isArray(docs) || docs.some(d => !d || typeof d !== "object" || typeof d.typ !== "string" || !Number.isInteger(d.id) || d.id <= 0)) {
        throw new CatalogueUpstreamError("SÚKL vrátil neočekávaný formát dokumentů.");
      }
      const doc = docs.find(d => d.typ.toUpperCase() === args.document_type);
      return { status: doc ? "ok" : "document_not_found", document: doc ? { sukl_code: code, medicine_name: medicine.name, type: args.document_type, url: `https://prehledy.sukl.cz/dlp/v1/dokumenty/${doc.id}`, content_included: false } : null, provenance };
    }
    case "display_medicines": {
      if (!Array.isArray(args.sukl_codes) || args.sukl_codes.length < 1 || args.sukl_codes.length > 10) throw new CatalogueInputError("sukl_codes musí obsahovat 1 až 10 kódů.");
      const codes = [...new Set(args.sukl_codes.map(catalogueCode))];
      const results = await Promise.all(codes.map(async code => ({ code, medicine: await getMedicineByCode(code) })));
      return { status: "ok", medicines: results.flatMap(r => r.medicine ? [catalogueMedicine(r.medicine)] : []), missing_codes: results.filter(r => !r.medicine).map(r => r.code), provenance };
    }
    default: throw new CatalogueInputError("Neznámý nástroj.");
  }
}
