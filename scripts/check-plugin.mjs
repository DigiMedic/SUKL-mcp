import { readFileSync } from "node:fs";
import { unzipSync, strFromU8 } from "fflate";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
const files = unzipSync(new Uint8Array(readFileSync("plugin-dist/sukl-medicines-1.0.0.zip")));
const manifest = JSON.parse(strFromU8(files["plugin.json"]));
const config = JSON.parse(strFromU8(files["mcp.json"]));
const ajv = new Ajv2020({ strict:false, allErrors:true }); addFormats(ajv);
for (const [schemaName,data] of [["plugin",manifest],["mcp",config]]) {
  const schema = JSON.parse(readFileSync(`tests/fixtures/${schemaName}.schema.json`,"utf8"));
  if (!ajv.validate(schema,data)) throw new Error(JSON.stringify(ajv.errors));
}
const openai = manifest.extensions["com.openai"], ui = openai.interface;
for (const [field,max] of [["displayName",30],["shortDescription",30],["longDescription",4000],["developerName",80]]) if (!ui[field] || [...ui[field]].length > max) throw new Error(`Neplatné pole ${field}.`);
for (const path of [ui.logo,ui.composerIcon,openai.onboardingSkill]) if(!path?.startsWith("./") || !files[path.slice(2)]) throw new Error("Chybí odkazovaný soubor.");
if (openai.apps || openai.hooks || files[".app.json"] || Object.keys(files).some(p => p.includes("..") || p.startsWith("/") || /(^|\/)\.env/.test(p))) throw new Error("Balíček obsahuje nepovolený obsah.");
if (Object.keys(config.mcpServers).length !== 1 || openai.review.test_cases.positive.length !== 5 || openai.review.test_cases.negative.length !== 3) throw new Error("Nesprávný počet serverů nebo review případů.");
console.log("ZIP: Agent Plugins schemas, OpenAI listing limits, files and 5 + 3 review cases passed.");
if (process.argv.includes("--live")) {
  if (!openai.review.demo_recording_url) throw new Error("Chybí veřejně dostupná nahrávka demonstrace (PLUGIN_DEMO_URL).");
  for (const url of [ui.websiteURL,ui.supportURL,ui.privacyPolicyURL,ui.termsOfServiceURL,openai.review.demo_recording_url]) {
    const res = await fetch(url,{signal:AbortSignal.timeout(10000)});
    if(!res.ok) throw new Error(`Veřejná stránka není připravena: ${url} (${res.status}).`);
  }
  const health = await fetch(new URL("/chatgpt/status",ui.websiteURL)).then(r => r.json());
  if(!health.ready_for_host_testing) throw new Error("Veřejné provozní předpoklady nejsou splněny: " + JSON.stringify(health.readiness));
  const client = new Client({name:"sukl-release-check",version:"1.0.0"});
  try {
    await client.connect(new StreamableHTTPClientTransport(new URL(config.mcpServers["sukl-catalogue"].url)));
    const {tools} = await client.listTools();
    if(tools.length !== 5 || tools.some(t => t.annotations?.readOnlyHint !== true || t.annotations?.destructiveHint !== false || t.annotations?.openWorldHint !== true)) throw new Error("Živé nástroje neodpovídají veřejné verzi.");
    const result = await client.callTool({name:"get_medicine",arguments:{sukl_code:"0254045"}});
    const validity = result.structuredContent?.provenance;
    if(result.isError || !validity?.source_as_of || !validity?.source_valid_until || validity.source_valid_until < new Date().toISOString().slice(0,10)) throw new Error("Živý katalog nemá aktuální ověřenou platnost.");
    const {contents} = await client.readResource({uri:"ui://sukl-catalogue/medicines-v1.html"});
    if(contents[0]?.mimeType !== "text/html;profile=mcp-app" || !contents[0]?._meta?.ui?.csp) throw new Error("Živý UI resource nebo CSP chybí.");
    console.log("Live readback: public pages, MCP negotiation, tool annotations, current catalogue and UI resource passed.");
  } finally { await client.close(); }
}
