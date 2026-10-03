import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { readFileSync } from "node:fs";
import { strFromU8 } from "fflate";
const length = value => [...value].length;
const nonempty = value => typeof value === "string" && value.trim().length > 0;
function luminance(hex) {
  const rgb = hex.slice(1).match(/../g).map(v => parseInt(v,16)/255).map(v => v <= 0.04045 ? v/12.92 : ((v+0.055)/1.055)**2.4);
  return 0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2];
}
export function isPublicHttps(value) {
  try { const u = new URL(value); return u.protocol === "https:" && !u.username && !u.password && !/^(localhost|127\.|\[?::1)/i.test(u.hostname); } catch { return false; }
}
export function validatePluginFiles(files) {
  const issues = [];
  const check = (valid, message) => { if (!valid) issues.push(message); };
  const manifest = JSON.parse(strFromU8(files["plugin.json"]));
  const config = JSON.parse(strFromU8(files["mcp.json"]));
  const ajv = new Ajv2020({ strict:false, allErrors:true }); addFormats(ajv);
  for (const [name,data] of [["plugin",manifest],["mcp",config]]) check(ajv.validate(JSON.parse(readFileSync(`tests/fixtures/${name}.schema.json`,"utf8")),data), `${name}: ${JSON.stringify(ajv.errors)}`);
  const openai = manifest.extensions?.["com.openai"] ?? {}, ui = openai.interface ?? {};
  for (const [field,max] of [["displayName",30],["shortDescription",30],["longDescription",4000],["developerName",80]]) check(typeof ui[field] === "string" && ui[field].trim() && length(ui[field]) <= max, `Listing: invalid ${field}.`);
  check(typeof ui.category === "string" && ui.category.trim(), "Listing: category is required; verify its exact title in the dashboard.");
  for (const field of ["websiteURL","supportURL","privacyPolicyURL","termsOfServiceURL"]) check(isPublicHttps(ui[field]) && length(ui[field]) <= 1024, `Listing: invalid ${field}.`);
  check(Array.isArray(ui.capabilities) && ui.capabilities.length <= 20 && ui.capabilities.every(v => typeof v === "string" && length(v) <= 120), "Listing: invalid capability labels.");
  for (const [field,background] of [["brandColor","#FFFFFF"],["brandColorDark","#212121"]]) if (ui[field] != null) {
    const format = typeof ui[field] === "string" && /^#[a-f0-9]{6}$/i.test(ui[field]);
    check(format, `Listing: invalid ${field}.`);
    if (format) { const foreground = luminance(ui[field]), base = luminance(background); check((Math.max(foreground,base)+0.05)/(Math.min(foreground,base)+0.05) >= 2, `Listing: insufficient ${field} contrast.`); }
  }
  const prompts = Array.isArray(ui.defaultPrompt) ? ui.defaultPrompt : ui.defaultPrompt ? [ui.defaultPrompt] : [];
  check(prompts.length <= 3 && new Set(prompts).size === prompts.length && prompts.every(v => typeof v === "string" && length(v) <= 128 && !v.includes("@")), "Listing: invalid starter prompts.");
  for (const path of [ui.logo,ui.composerIcon,openai.onboardingSkill]) check(typeof path === "string" && path.startsWith("./") && files[path.slice(2)], "Package: referenced icon or onboarding skill is absent.");
  for (const path of new Set([ui.logo,ui.composerIcon])) if (path && files[path.slice(2)]) {
    const data = files[path.slice(2)]; check(data.length <= 5 * 1024 * 1024, "Icon exceeds 5 MiB.");
    const svg = strFromU8(data); const box = svg.match(/viewBox=["']\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)["']/);
    check(path.endsWith(".svg") && box && Number(box[3]) === Number(box[4]) && Number(box[3]) >= 48 && !/<script|<foreignObject|(?:href|src)=["']https?:/i.test(svg), "Icon: expected a self-contained square SVG of at least 48 px.");
  }
  const skill = openai.onboardingSkill && files[openai.onboardingSkill.slice(2)];
  if (skill) { const text = strFromU8(skill); check(/^---\r?\n/.test(text) && /^name:\s*get-started\s*$/m.test(text) && /^description:\s*\S.+$/m.test(text), "Onboarding skill requires valid name/description front matter."); }
  check(!openai.apps && !openai.hooks && !files[".app.json"] && Object.keys(files).every(p => !p.split("/").includes("..") && !p.startsWith("/") && !/(^|\/)\.env/.test(p)), "Package contains unsupported app references, hooks or unsafe paths.");
  const servers = Object.values(config.mcpServers ?? {}); check(servers.length === 1 && servers[0]?.type === "streamable-http" && isPublicHttps(servers[0]?.url), "Expected one public streamable HTTP MCP server.");
  const cases = openai.review?.test_cases ?? {};
  for (const [kind,count] of [["positive",5],["negative",3]]) check(Array.isArray(cases[kind]) && cases[kind].length === count && cases[kind].every(c => nonempty(c.description) && nonempty(c.prompt) && (kind === "negative" || nonempty(c.tools_triggered) && nonempty(c.expected_behavior))), `Review: expected ${count} complete ${kind} cases.`);
  check(!openai.review?.test_credentials && !openai.review?.reviewer_instructions, "Review: private access information must stay outside the ZIP.");
  check(openai.review?.commerce === false, "This catalogue must declare commerce=false.");
  if (openai.review?.demo_recording_url) check(isPublicHttps(openai.review.demo_recording_url), "Review: invalid video URL.");
  const countries = openai.publication?.countries; check(Array.isArray(countries) && countries.every(c => /^[A-Z]{2}$/.test(c)), "Publication: invalid country allowlist.");
  for (const [locale,translation] of Object.entries(openai.publication?.translations ?? {})) { check(locale.trim(), "Publication: empty locale."); for (const [key,max] of [["subtitle",30],["description",4000]]) if (translation[key] != null) check(typeof translation[key] === "string" && length(translation[key]) <= max, `Publication: invalid ${locale}.${key}.`); }
  return { manifest, config, issues };
}
