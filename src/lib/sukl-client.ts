/**
 * SÚKL Client - Data access layer for Czech medicines database
 * Uses bundled JSON data for Vercel serverless compatibility
 */

import Fuse, { type IFuseOptions } from "fuse.js";
import { readFileSync } from "fs";
import { join } from "path";
import type {
  MedicineBasic,
  MedicineDetail,
  ReimbursementInfo,
  AvailabilityInfo,
  Pharmacy,
  ATCInfo,
  DocumentContent,
} from "./types";

// ============================================================================
// Lazy-load bundled data (server-only, not imported at module level)
// ============================================================================

let _bundledData: BundledData | null = null;
function getBundledData(): BundledData {
  if (!_bundledData) {
    const dataPath = join(process.cwd(), "data/bundled-data.json");
    try {
      _bundledData = JSON.parse(
        readFileSync(dataPath, "utf-8")
      ) as BundledData;
    } catch (error) {
      console.error(`Failed to load bundled data from ${dataPath}:`, error);
      throw new Error("SÚKL data file is missing or corrupted. Ensure data/bundled-data.json exists.");
    }
  }
  return _bundledData;
}

// ============================================================================
// Types for bundled data
// ============================================================================

interface BundledMedicine {
  c: string;  // code
  n: string;  // name
  s: string;  // strength
  f: string;  // form
  p: string;  // package (balení)
  a: string;  // atc
  u: string;  // substance
  h: string;  // holder
  r: string;  // registration
  d: string;  // dispensing
  rn?: string; rv?: string | null; ro?: string | null; ig?: string | null; mr?: string | null; pi?: boolean;
}

interface BundledATC {
  c: string;  // code
  n: string;  // name
  en?: string | null;
  l: number;  // level
  p: string;  // parent
}

interface BundledPharmacy {
  n: string;   // name (NAZEV)
  k: string;   // workplace code (KOD_PRACOVISTE)
  a: string;   // address (ULICE)
  c: string;   // city (MESTO)
  z: string;   // postal code (PSC)
  t: string;   // phone (TELEFON)
  e: string;   // email (EMAIL)
  w: string;   // web (WWW)
  r: boolean;  // has eRecept (ERP)
  h: boolean;  // is 24h emergency (POHOTOVOST)
}

interface BundledReimbursement {
  c: string;        // sukl_code
  g: string | null;  // reimbursement_group
  m: number | null;  // max_price
  a: number | null;  // reimbursement_amount
  s: number | null;  // patient_surcharge
  o?: string | null;
}

interface BundledData {
  m: BundledMedicine[];
  a: BundledATC[];
  p?: BundledPharmacy[];
  r?: BundledReimbursement[];
  _: {
    t: string;
    c: { m: number; a: number; p?: number; r?: number };
    sources?: { medicines?: { url: string; valid_from: string; valid_until: string }; reimbursements?: { url: string; valid_from: string } };
  };
}

// ============================================================================
// Data Storage (in-memory cache)
// ============================================================================

interface DataStore {
  medicines: MedicineDetail[];
  medicinesByCode: Map<string, MedicineDetail>;
  reimbursements: Map<string, ReimbursementInfo>;
  atcCodes: Map<string, ATCInfo>;
  pharmacies: Pharmacy[];
  lastLoaded: Date | null;
  fuseIndex: Fuse<MedicineDetail> | null;
}

const store: DataStore = {
  medicines: [],
  medicinesByCode: new Map(),
  reimbursements: new Map(),
  atcCodes: new Map(),
  pharmacies: [],
  lastLoaded: null,
  fuseIndex: null,
};

// ============================================================================
// Configuration
// ============================================================================

const FUSE_OPTIONS: IFuseOptions<MedicineDetail> = {
  keys: [
    { name: "name", weight: 0.4 },
    { name: "substance", weight: 0.3 },
    { name: "sukl_code", weight: 0.2 },
    { name: "holder", weight: 0.1 },
  ],
  threshold: 0.3,
  ignoreLocation: true,
  includeScore: true,
  minMatchCharLength: 2,
};

// ============================================================================
// Data Loading from bundled JSON
// ============================================================================

function normalizeCode(code: string): string {
  return code.replace(/^0+/, "") || "0";
}

function transformBundledMedicine(m: BundledMedicine): MedicineDetail {
  return {
    sukl_code: normalizeCode(m.c),
    name: m.n,
    strength: m.s || null,
    form: m.f || null,
    package: m.p || null,
    atc_code: m.a || null,
    substance: m.u || null,
    holder: m.h || null,
    registration_status: m.r || null,
    registration_number: m.rn || null,
    registration_valid_until: m.rv || null,
    dispensing: m.d || null,
    legal_status: null,
    route_of_administration: m.ro || null,
    indication_group: m.ig || null,
    mrp_number: m.mr || null,
    parallel_import: m.pi ?? null,
  };
}

function transformBundledPharmacy(p: BundledPharmacy): Pharmacy {
  return {
    id: p.k,
    name: p.n,
    address: p.a,
    city: p.c,
    postal_code: p.z,
    phone: p.t || null,
    email: p.e || null,
    opening_hours: null,
    latitude: null,
    longitude: null,
    distance_km: null,
    is_24h: null,
    has_emergency_service: p.h,
    has_erecept: p.r,
  };
}

function transformBundledReimbursement(r: BundledReimbursement): ReimbursementInfo {
  return {
    sukl_code: normalizeCode(r.c),
    reimbursement_group: r.g,
    max_price: r.m,
    reimbursement_amount: r.a,
    patient_surcharge: r.s,
    reimbursement_conditions: r.o || null,
    valid_from: getBundledData()._.sources?.reimbursements?.valid_from ?? null,
    valid_until: null,
  };
}

function transformBundledATC(a: BundledATC, knownCodes: Set<string>): ATCInfo {
  const lengths = [1, 3, 4, 5, 7];
  const level = lengths.indexOf(a.c.length) + 1;
  return {
    code: a.c,
    name_cs: a.n,
    name_en: a.en || null,
    level,
    parent_code: level > 1 && knownCodes.has(a.c.slice(0, lengths[level - 2])) ? a.c.slice(0, lengths[level - 2]) : null,
    description: null,
  };
}

export async function initializeData(): Promise<void> {
  if (store.lastLoaded) {
    return;
  }

  console.log("Loading SÚKL data from bundle...");

  const data = getBundledData();

  // Transform medicines and build code→medicine Map
  store.medicines = data.m.map(transformBundledMedicine);
  store.medicinesByCode.clear();
  for (const med of store.medicines) {
    store.medicinesByCode.set(med.sukl_code, med);
  }

  // Build Fuse index
  store.fuseIndex = new Fuse(store.medicines, FUSE_OPTIONS);

  // Transform ATC codes
  store.atcCodes.clear();
  const knownCodes = new Set(data.a.map(a => a.c));
  for (const a of data.a) {
    const info = transformBundledATC(a, knownCodes);
    store.atcCodes.set(info.code, info);
  }

  // Transform pharmacies (if available)
  if (data.p) {
    store.pharmacies = data.p.map(transformBundledPharmacy);
  }

  // Transform reimbursements (if available)
  if (data.r) {
    store.reimbursements.clear();
    for (const r of data.r) {
      const info = transformBundledReimbursement(r);
      store.reimbursements.set(normalizeCode(info.sukl_code), info);
    }
  }

  store.lastLoaded = new Date();
  console.log(
    `Loaded ${store.medicines.length} medicines, ${store.atcCodes.size} ATC codes, ${store.pharmacies.length} pharmacies, ${store.reimbursements.size} reimbursements from bundle`
  );
}

// ============================================================================
// Public API
// ============================================================================

function toBasic(m: MedicineDetail): MedicineBasic {
  return {
    sukl_code: m.sukl_code,
    name: m.name,
    strength: m.strength,
    form: m.form,
    package: m.package,
    atc_code: m.atc_code,
    substance: m.substance,
    holder: m.holder,
    registration_status: m.registration_status,
  };
}

export async function searchMedicines(
  query: string,
  limit: number = 20
): Promise<{
  medicines: MedicineBasic[];
  total_count: number;
  search_time_ms: number;
}> {
  await initializeData();

  const startTime = performance.now();

  if (!store.fuseIndex || store.medicines.length === 0) {
    return { medicines: [], total_count: 0, search_time_ms: 0 };
  }

  const exact = /^\d{1,7}$/.test(query.trim())
    ? store.medicinesByCode.get(normalizeCode(query.trim()))
    : undefined;
  const results = exact
    ? [{ item: exact }]
    : store.fuseIndex.search(query);

  return {
    medicines: results.slice(0, limit).map((r) => toBasic(r.item)),
    total_count: results.length,
    search_time_ms: Math.round(performance.now() - startTime),
  };
}

/** Bundle creation time is not a verified source publication date. */
export function getCatalogueProvenance() {
  const source = getBundledData()._.sources?.medicines;
  const today = new Date().toISOString().slice(0, 10);
  const freshness = !source ? "unverified" : today < source.valid_from ? "not_yet_valid" : today > source.valid_until ? "expired" : "current";
  return {
    freshness,
    bundle_created_at: getBundledData()._.t,
    source_as_of: getBundledData()._.sources?.medicines?.valid_from ?? null,
    source_valid_until: getBundledData()._.sources?.medicines?.valid_until ?? null,
    source_url: getBundledData()._.sources?.medicines?.url ?? "https://opendata.sukl.gov.cz/",
    warning: `${freshness === "expired" ? "Platnost snímku skončila; nelze jej považovat za aktuální. " : freshness === "not_yet_valid" ? "Snímek ještě není účinný. " : ""}Katalog z veřejných dat SÚKL. Neověřuje skladovou dostupnost, aktuální prodejní ceny ani nárok na úhradu. Složení, zejména kombinovaných přípravků, ověřte v oficiálním PIL/SPC.`,
  };
}

export async function getMedicineByCode(
  suklCode: string
): Promise<MedicineDetail | null> {
  await initializeData();
  return store.medicinesByCode.get(normalizeCode(suklCode)) ?? null;
}

export async function getReimbursement(
  suklCode: string
): Promise<ReimbursementInfo | null> {
  await initializeData();
  return store.reimbursements.get(normalizeCode(suklCode)) ?? null;
}

export async function getATCInfo(
  atcCode: string
): Promise<ATCInfo | null> {
  await initializeData();
  return store.atcCodes.get(atcCode) || null;
}

export async function getMedicinesByATC(
  atcCode: string
): Promise<MedicineBasic[]> {
  await initializeData();

  return store.medicines
    .filter((m) => m.atc_code?.startsWith(atcCode))
    .map(toBasic);
}

export async function checkAvailability(
  suklCode: string
): Promise<AvailabilityInfo | null> {
  await initializeData();

  const medicine = await getMedicineByCode(suklCode);
  if (!medicine) return null;

  return {
    sukl_code: medicine.sukl_code,
    name: medicine.name,
    status: "unknown",
    last_checked: null,
    distribution_status: null,
    expected_availability: null,
    notes:
      "Skutečnou skladovou dostupnost tento server neověřuje. Registrace není dostupnost.",
  };
}

const SUKL_API_BASE = "https://prehledy.sukl.cz/dlp/v1";

interface SuklDocumentMeta {
  id: number;
  typ: string;
  nazev: string;
}

export async function getDocumentContent(
  suklCode: string,
  documentType: "PIL" | "SPC"
): Promise<DocumentContent | null> {
  const medicine = await getMedicineByCode(suklCode);
  if (!medicine) return null;

  try {
    const res = await fetch(
      `${SUKL_API_BASE}/dokumenty-metadata/${suklCode.padStart(7, "0")}`,
      { signal: AbortSignal.timeout(8000), cache: "no-store" }
    );

    if (!res.ok) {
      return {
        sukl_code: suklCode,
        document_type: documentType,
        title: `${documentType} - ${medicine.name}`,
        content: `Dokumenty pro ${medicine.name} nejsou v SÚKL API k dispozici (HTTP ${res.status}).`,
        sections: [],
        last_updated: null,
        language: "cs",
        document_url: null,
      };
    }

    const raw: unknown = await res.json();
    if (!Array.isArray(raw) || raw.some(d => !d || typeof d.typ !== "string" || !Number.isInteger(d.id) || d.id <= 0)) throw new Error("Neplatná metadata SÚKL.");
    const docs = raw as SuklDocumentMeta[];
    const doc = docs.find(
      (d) => d.typ.toUpperCase() === documentType
    );

    if (!doc) {
      return {
        sukl_code: suklCode,
        document_type: documentType,
        title: `${documentType} - ${medicine.name}`,
        content: `Dokument ${documentType} pro ${medicine.name} není k dispozici.`,
        sections: [],
        last_updated: null,
        language: "cs",
        document_url: null,
      };
    }

    const downloadUrl = `${SUKL_API_BASE}/dokumenty/${doc.id}`;

    return {
      sukl_code: suklCode,
      document_type: documentType,
      title: `${documentType} - ${medicine.name}`,
      content: `Dokument ${documentType} pro přípravek ${medicine.name} je dostupný ke stažení. Obsah PDF není součástí odpovědi; pro informace otevřete oficiální dokument.`,
      sections: [],
      last_updated: null,
      language: "cs",
      document_url: downloadUrl,
    };
  } catch {
    return {
      sukl_code: suklCode,
      document_type: documentType,
      title: `${documentType} - ${medicine.name}`,
      content: `Nepodařilo se získat dokument z SÚKL API.`,
      sections: [],
      last_updated: null,
      language: "cs",
      document_url: null,
    };
  }
}

export async function findPharmacies(
  city?: string,
  postalCode?: string,
  is24h?: boolean
): Promise<Pharmacy[]> {
  await initializeData();

  let results = store.pharmacies;

  if (city) {
    results = results.filter((p) =>
      p.city.toLowerCase().includes(city.toLowerCase())
    );
  }

  if (postalCode) {
    results = results.filter((p) => p.postal_code.startsWith(postalCode));
  }

  if (is24h !== undefined) throw new Error("Údaj o nepřetržitém provozu není ověřen. Použijte kontaktní údaje lékárny.");

  return results;
}
