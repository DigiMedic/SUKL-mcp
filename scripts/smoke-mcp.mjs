import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { writeFileSync } from "node:fs";
const base = process.argv[2];
if (!base) throw new Error("Zadejte veřejný HTTPS nebo místní testovací origin.");
const evidence = { origin:base, checks:[] };
for (const [path,legacy] of [["/chatgpt/mcp",false],["/mcp",true]]) {
  const url = new URL(path,base);
  const client = new Client({name:"sukl-smoke",version:"1.0.0"});
  try {
    await client.connect(new StreamableHTTPClientTransport(url));
    const {tools} = await client.listTools();
    if (tools.length !== (legacy ? 9 : 5)) throw new Error("Unexpected tool count.");
    const results = {};
    const operations = legacy ? [
      ["get-reimbursement",{sukl_code:"0094156"}],
      ["batch-check-availability",{sukl_codes:["0254045","9999999"]}],
      ["find-pharmacies",{city:"Praha",limit:2}],
    ] : [
      ["search_medicines",{query:"0254045",limit:1}],
      ["get_medicine",{sukl_code:"0000009"}],
      ["get_atc_group",{atc_code:"N02BE01",limit:2}],
      ["get_medicine_document",{sukl_code:"0254045",document_type:"PIL"}],
      ["display_medicines",{sukl_codes:["0254045","9999999"]}],
    ];
    for (const [name,args] of operations) {
      const result = await client.callTool({name,arguments:args});
      if(result.isError) throw new Error(`${name} returned an error.`);
      results[name] = result.structuredContent;
    }
    if (!legacy) {
      const resource = await client.readResource({uri:"ui://sukl-catalogue/medicines-v2.html"});
      evidence.widget = { mimeType:resource.contents[0].mimeType, csp:resource.contents[0]._meta?.ui?.csp, byteLength:new TextEncoder().encode(resource.contents[0].text).length };
    }
    evidence.checks.push({path,tool_count:tools.length,results});
  } finally { await client.close(); }
}
for (const [path,expected] of [["/chatgpt/mcp",405],["/mcp",405],["/chatgpt",200],["/chatgpt/support",200],["/api/chatgpt/preview",404]]) {
  const response = await fetch(new URL(path,base));
  if(response.status !== expected) throw new Error(`${path} returned ${response.status}, expected ${expected}.`);
  evidence.checks.push({path,status:response.status});
}
const blockedOrigin = await fetch(new URL("/chatgpt/mcp",base),{method:"POST",headers:{Origin:"https://evil.example.test","Content-Type":"application/json",Accept:"application/json, text/event-stream"},body:JSON.stringify({jsonrpc:"2.0",id:1,method:"ping"})});
if(blockedOrigin.status !== 403) throw new Error("Untrusted origin was not rejected.");
evidence.checks.push({path:"/chatgpt/mcp",untrusted_origin_status:blockedOrigin.status});
writeFileSync("plugin-dist/mcp-smoke-evidence.json",JSON.stringify(evidence,null,2));
console.log("Network SDK checks passed for both endpoints, live SÚKL PIL metadata, UI resource, HTTP methods and pages.");
