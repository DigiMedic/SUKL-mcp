const nullableText = { type: ["string", "null"] };
const code = { type: "string", pattern: "^[0-9]{7}$" };
export const SUKL_DATA_TERMS_URL = "https://opendata.sukl.gov.cz/?q=podminky-uziti-otevrenych-dat";
const medicine = {
  type: "object", required: ["sukl_code", "name", "strength", "form", "package", "atc_code", "reported_substance", "source_url"],
  properties: { sukl_code: code, name: { type: "string" }, strength: nullableText, form: nullableText, package: nullableText, atc_code: nullableText, reported_substance: nullableText, source_url: { type: "string", format: "uri" }, dispensing_code: nullableText, registration_status_code: nullableText },
};
const medicines = { type: "array", items: medicine };
const provenance = {
  type: "object", required: ["freshness", "bundle_created_at", "source_as_of", "source_valid_until", "source_url", "source_name", "terms_url", "warning"],
  properties: { freshness: { enum: ["current", "expired", "not_yet_valid", "unverified"] }, bundle_created_at: { type: "string" }, source_as_of: nullableText, source_valid_until: nullableText, source_url: { type: "string", format: "uri" }, source_name: { const: "SÚKL" }, terms_url: { const: SUKL_DATA_TERMS_URL }, warning: { type: "string" } },
};
function result(status: string[], properties: Record<string, unknown>) {
  return { type: "object" as const, required: ["status", "provenance", ...Object.keys(properties)], properties: { status: { enum: status }, provenance, ...properties } };
}
export const CATALOGUE_OUTPUT_SCHEMAS = {
  search_medicines: result(["ok", "no_match"], { medicines, total_count: { type: "integer", minimum: 0 } }),
  get_medicine: result(["ok", "not_found"], { medicine: { anyOf: [medicine, { type: "null" }] } }),
  get_atc_group: result(["ok", "not_found"], { atc: { anyOf: [{ type: "object", required: ["code", "name_cs", "name_en", "level", "parent_code", "description"], properties: { code: { type: "string" }, name_cs: { type: "string" }, name_en: nullableText, level: { type: "integer", minimum: 1, maximum: 5 }, parent_code: nullableText, description: nullableText } }, { type: "null" }] }, medicines, total_count: { type: "integer", minimum: 0 } }),
  get_medicine_document: result(["ok", "not_found", "document_not_found"], { document: { anyOf: [{ type: "object", required: ["sukl_code", "medicine_name", "type", "url", "content_included"], properties: { sukl_code: code, medicine_name: { type: "string" }, type: { enum: ["PIL", "SPC"] }, url: { type: "string", pattern: "^https://prehledy\\.sukl\\.cz/dlp/v1/dokumenty/[0-9]+$" }, content_included: { const: false } } }, { type: "null" }] } }),
  display_medicines: result(["ok"], { medicines: { ...medicines, maxItems: 10 }, missing_codes: { type: "array", items: code, maxItems: 10 } }),
};
