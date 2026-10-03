import { readFileSync, writeFileSync } from "node:fs";
import { unzipSync } from "fflate";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { validatePluginFiles } from "./plugin-validation.mjs";
const source = JSON.parse(readFileSync("plugins/sukl-medicines/plugin.json","utf8"));
const files = unzipSync(new Uint8Array(readFileSync(`plugin-dist/sukl-medicines-${source.version}.zip`)));
const { manifest, config, issues } = validatePluginFiles(files);
const report = { checked_at:new Date().toISOString(), plugin_version:manifest.version, scope:process.argv.includes("--live") ? "public-technical-readiness" : "offline-package", checks:[], blockers:[...issues], host_evaluation:"Not established by this script: run direct, indirect and negative prompts in ChatGPT on desktop and mobile; verify identity, domain and review in the OpenAI portal." };
async function check(name, operation) {
  try { const detail = await operation(); report.checks.push({ name, passed:true, detail }); }
  catch (error) { const detail = error.message; report.checks.push({ name, passed:false, detail }); report.blockers.push(`${name}: ${detail}`); }
}
const openai = manifest.extensions?.["com.openai"], ui = openai?.interface;
if (process.argv.includes("--live") && issues.length === 0) {
  await check("review-video",async () => { const url = openai.review.demo_recording_url; if (!url) throw new Error("Chybí skutečné demo video (PLUGIN_DEMO_URL)."); const r = await fetch(url,{signal:AbortSignal.timeout(10000)}); if (!r.ok) throw new Error(`HTTP ${r.status}`); return {url,status:r.status}; });
  for (const field of ["websiteURL","supportURL","privacyPolicyURL","termsOfServiceURL"]) await check(field,async () => { const r = await fetch(ui[field],{signal:AbortSignal.timeout(10000)}); if (!r.ok) throw new Error(`HTTP ${r.status}: ${ui[field]}`); return {url:ui[field],status:r.status}; });
  await check("deployment-readiness",async () => { const r = await fetch(new URL("/chatgpt/status",ui.websiteURL),{signal:AbortSignal.timeout(10000)}); if (!r.ok) throw new Error(`HTTP ${r.status}`); const health = await r.json(); if (!health.ready_for_host_testing) throw new Error(JSON.stringify(health.readiness)); return health.readiness; });
  await check("live-mcp",async () => {
    const client = new Client({name:"sukl-release-check",version:"1.0.1"});
    try {
      await client.connect(new StreamableHTTPClientTransport(new URL(Object.values(config.mcpServers)[0].url)),{timeout:10000});
      const {tools} = await client.listTools();
      if(tools.length !== 5 || tools.some(t => t.annotations?.readOnlyHint !== true || t.annotations?.destructiveHint !== false || t.annotations?.openWorldHint !== true || !t.outputSchema)) throw new Error("Nástroje nebo schémata neodpovídají veřejné verzi.");
      const result = await client.callTool({name:"get_medicine",arguments:{sukl_code:"0254045"}});
      const validity = result.structuredContent?.provenance;
      if(result.isError || validity?.freshness !== "current") throw new Error("Katalog nemá aktuální ověřenou platnost.");
      const uri = tools.find(t => t.name === "display_medicines")?._meta?.ui?.resourceUri;
      if(typeof uri !== "string") throw new Error("Chybí propojení vykreslovacího nástroje.");
      const {contents} = await client.readResource({uri});
      if(contents[0]?.mimeType !== "text/html;profile=mcp-app" || !contents[0]?._meta?.ui?.csp) throw new Error("UI resource nebo CSP chybí.");
      return {tool_count:tools.length,resource_uri:uri,freshness:validity.freshness};
    } finally { await client.close(); }
  });
}
report.passed = report.blockers.length === 0;
writeFileSync("plugin-dist/validation-report.json",JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify(report,null,2));
if (!report.passed) process.exitCode = 1;
