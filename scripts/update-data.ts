/** Discover current official releases; validate all inputs before atomically replacing the bundle. */
import { readFileSync, writeFileSync, renameSync } from "node:fs";
import { createHash } from "node:crypto";
import { unzipSync } from "fflate";
import { parseDelimited, parseScau } from "./data-parser";

const DLP_PAGE = "https://opendata.sukl.gov.cz/?q=katalog/databaze-lecivych-pripravku-dlp";
const CAU_PAGE = "https://sukl.gov.cz/ceny-a-uhrady-leciv/seznam-cen-a-uhrad-lp/";
const PHARMACIES = "https://opendata.sukl.cz/soubory/NKOD/LEKARNY/nkod_lekarny_seznam.csv";
async function download(url: string) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || !["sukl.gov.cz", "opendata.sukl.cz", "opendata.sukl.gov.cz"].includes(parsed.hostname)) throw new Error("Neočekávaný zdroj dat.");
  const res = await fetch(url, { signal: AbortSignal.timeout(60_000) });
  if (!res.ok) throw new Error(`Zdroj dat není dostupný (${res.status}).`);
  const data = new Uint8Array(await res.arrayBuffer());
  if (data.length > 100 * 1024 * 1024) throw new Error("Zdroj překročil limit velikosti.");
  return data;
}
const utf8 = (bytes: Uint8Array) => new TextDecoder().decode(bytes);
const cp1250 = (bytes: Uint8Array) => new TextDecoder("windows-1250").decode(bytes);
const hash = (bytes: Uint8Array) => createHash("sha256").update(bytes).digest("hex");
const iso = (value: string) => {
  if (!/^\d{2}\.\d{2}\.\d{4}$/.test(value)) throw new Error("Neplatné datum platnosti DLP.");
  return value.split(".").reverse().join("-");
};

async function main() {
  const dlpPage = utf8(await download(DLP_PAGE));
  const dlpUrls = [...dlpPage.matchAll(/href="(https:\/\/opendata\.sukl\.cz\/soubory\/SOD\d{8}\/DLP\d{8}\.zip)"/g)].map(m => m[1]).sort().reverse();
  if (!dlpUrls[0]) throw new Error("Aktuální archiv DLP nebyl nalezen.");
  const cauPage = utf8(await download(CAU_PAGE));
  const category = cauPage.match(/&quot;categories&quot;:\[&quot;(\d+)&quot;\]/)?.[1];
  if (!category) throw new Error("Kategorie SCAU nebyla nalezena.");
  const posts: {link: string; content: {rendered: string}}[] = JSON.parse(utf8(await download(`https://sukl.gov.cz/wp-json/wp/v2/posts?categories=${category}&per_page=20&_fields=link,content,date`)));
  const releaseDate = (url: string) => { const d = url.match(/-k-(\d+)-(\d+)-(\d{4})\//); return d ? `${d[3]}-${d[2].padStart(2,"0")}-${d[1].padStart(2,"0")}` : ""; };
  const releases = posts.filter(p => releaseDate(p.link) && releaseDate(p.link) <= new Date().toISOString().slice(0,10));
  const release = releases.find(p => /SCAU\d{6}v21(?:-\d+)?\.txt/.test(p.content.rendered));
  const scauUrl = release?.content.rendered.match(/href="(https:\/\/sukl\.gov\.cz\/wp-content\/uploads\/\d{4}\/\d{2}\/SCAU\d{6}v21(?:-\d+)?\.txt)"/)?.[1];
  if (!scauUrl || !release) throw new Error("Aktuální SCAU v21 nebyl nalezen; změna schématu vyžaduje kontrolu.");
  const dlpBytes = await download(dlpUrls[0]);
  const files = unzipSync(dlpBytes, { filter: file => ["dlp_lecivepripravky.csv", "dlp_slozeni.csv", "dlp_lecivelatky.csv", "dlp_organizace.csv", "dlp_atc.csv", "dlp_platnost.csv"].includes(file.name) });
  const csv = (name: string) => { if (!files[name]) throw new Error(`Chybí ${name}.`); return parseDelimited(cp1250(files[name])); };
  const substances = new Map(csv("dlp_lecivelatky.csv").map(r => [r.KOD_LATKY, r.NAZEV_INN || r.NAZEV]));
  const ingredients = new Map<string, Set<string>>();
  for (const r of csv("dlp_slozeni.csv")) {
    const name = substances.get(r.KOD_LATKY);
    if (r.S === "L" && name) { const set = ingredients.get(r.KOD_SUKL) ?? new Set<string>(); set.add(name); ingredients.set(r.KOD_SUKL, set); }
  }
  const organisations = new Map(csv("dlp_organizace.csv").map(r => [`${r.ZKR_ORG}|${r.ZEM}`, r.NAZEV]));
  const m = csv("dlp_lecivepripravky.csv").map(r => {
    if (!/^\d{7}$/.test(r.KOD_SUKL) || !r.NAZEV || !r.REG || !("VYDEJ" in r)) throw new Error("Neplatný záznam DLP nebo změněná hlavička.");
    return { c: r.KOD_SUKL, n: r.NAZEV, s: r.SILA, f: r.FORMA, p: r.BALENI, a: r.ATC_WHO, u: [...(ingredients.get(r.KOD_SUKL) ?? [])].join("; "), h: organisations.get(`${r.AKT_DRZ || r.DRZ}|${r.AKT_ZEM || r.ZEMDRZ}`) || r.DRZ, r: r.REG, d: r.VYDEJ, rn: r.RC, rv: r.V_PLATDO ? (/^\d{6}$/.test(r.V_PLATDO) ? `20${r.V_PLATDO.slice(4)}-${r.V_PLATDO.slice(2,4)}-${r.V_PLATDO.slice(0,2)}` : iso(r.V_PLATDO)) : null, ro: r.CESTA || null, ig: r.IS_ || null, mr: r.MRP_CISLO || null, pi: r.SDOV ? true : false };
  });
  const lengths = [1, 3, 4, 5, 7];
  const a = csv("dlp_atc.csv").map(r => { const level = lengths.indexOf(r.ATC.length) + 1; if (!level || !r.NAZEV) throw new Error("Neplatné ATC."); return { c: r.ATC, n: r.NAZEV, en: r.NAZEV_EN || null, l: level, p: level > 1 ? r.ATC.slice(0, lengths[level - 2]) : "" }; });
  const atcSet = new Set(a.map(r => r.c));
  if (m.length < 30000 || a.length < 5000 || new Set(m.map(r => r.c)).size !== m.length || m.some(r => r.a && !atcSet.has(r.a))) throw new Error("Katalog nesplnil kontrolu počtů, jedinečnosti nebo referencí.");
  const hierarchyGaps = a.filter(r => r.p && !atcSet.has(r.p)).map(r => r.c);
  for (const row of a) if (row.p && !atcSet.has(row.p)) row.p = "";
  const pharmacyBytes = await download(PHARMACIES);
  const p = parseDelimited(utf8(pharmacyBytes), ",").map(r => {
    if (!r.KOD_PRACOVISTE || !r.NAZEV || !("POHOTOVOST" in r)) throw new Error("Neplatné lékárenské CSV.");
    return { n:r.NAZEV, k:r.KOD_PRACOVISTE, a:r.ULICE, c:r.MESTO, z:r.PSC, t:r.TELEFON, e:r.EMAIL, w:r.WWW, r:r.ERP === "1", h:r.POHOTOVOST === "1" };
  });
  if (p.length < 1000 || new Set(p.map(r => r.k)).size !== p.length) throw new Error("Neplatný počet nebo duplicita lékáren.");
  const scauBytes = await download(scauUrl);
  const r = parseScau(cp1250(scauBytes));
  if (r.length < 5000) throw new Error("SCAU obsahuje nečekaně málo záznamů.");
  const validity = csv("dlp_platnost.csv")[0];
  const sources = { medicines: { url:dlpUrls[0], sha256:hash(dlpBytes), valid_from:iso(validity.platnost_od), valid_until:iso(validity.platnost_do), atc_hierarchy_gaps:hierarchyGaps }, pharmacies: { url:PHARMACIES, sha256:hash(pharmacyBytes) }, reimbursements: { url:scauUrl, sha256:hash(scauBytes), valid_from:releaseDate(release.link) } };
  const path = "data/bundled-data.json";
  const previous = JSON.parse(readFileSync(path, "utf8"));
  if (JSON.stringify({m,a,p,r,sources}) === JSON.stringify({m:previous.m,a:previous.a,p:previous.p,r:previous.r,sources:previous._.sources})) { console.log("Zdroje i obsah jsou beze změny."); return; }
  const bundle = { m,a,p,r,_:{ t:new Date().toISOString(), c:{m:m.length,a:a.length,p:p.length,r:r.length}, sources } };
  writeFileSync(`${path}.tmp`, JSON.stringify(bundle)); renameSync(`${path}.tmp`, path);
  const medicineCodes = new Set(m.map(med => med.c));
  console.log(JSON.stringify({ counts:bundle._.c, sources, reimbursements_without_catalogue_match:r.filter(item => !medicineCodes.has(item.c)).length }));
}
main().catch(error => { console.error("Aktualizace dat selhala; původní balíček zůstal zachován.", error.message); process.exitCode = 1; });
