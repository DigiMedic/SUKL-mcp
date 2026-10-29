import { describe, it, expect, vi, afterEach } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { handleCatalogueHttp, CHATGPT_TOOLS, CATALOGUE_UI_URI } from "@/lib/chatgpt-mcp";
import { createLegacyServer } from "@/lib/legacy-mcp";
import { catalogueOperation } from "@/lib/chatgpt-catalogue";
import { getATCInfo, searchMedicines, getMedicineByCode } from "@/lib/sukl-client";

const url = "http://localhost:3137/api/chatgpt/mcp";
async function client(legacy = false) {
  const c = new Client({ name:"test", version:"1" });
  const transport = new StreamableHTTPClientTransport(new URL(url), { fetch: (async (input: RequestInfo | URL, init?: RequestInit) => handleCatalogueHttp(new Request(input, init), legacy ? createLegacyServer : undefined)) as typeof fetch });
  await c.connect(transport); return c;
}
afterEach(() => { vi.unstubAllGlobals(); });

describe("Published MCP transport and catalogue", () => {
  it("negotiates via the real SDK client, lists annotated tools and reads the self-contained UI", async () => {
    const c = await client();
    try {
      const { tools } = await c.listTools(); expect(tools).toHaveLength(5);
      for (const t of tools) expect(t.annotations).toMatchObject({readOnlyHint:true,destructiveHint:false,openWorldHint:true});
      expect(CHATGPT_TOOLS.filter(t => (t._meta?.ui as {resourceUri?:string})?.resourceUri)).toHaveLength(1);
      const resource = await c.readResource({uri:CATALOGUE_UI_URI});
      const item = resource.contents[0]; expect(item.mimeType).toBe("text/html;profile=mcp-app");
      expect(item._meta).toMatchObject({ui:{csp:{connectDomains:[],resourceDomains:[]}}});
      expect("text" in item && item.text).toContain("České léčivé přípravky");
      expect("text" in item && item.text).not.toMatch(/<script[^>]+src=/);
      expect("text" in item && item.text).not.toContain("/api/chatgpt/preview-data");
    } finally { await c.close(); }
  });
  it("returns an exact seven-digit code, valid provenance and all relevant ingredients", async () => {
    const c = await client();
    try {
      const result = await c.callTool({name:"search_medicines",arguments:{query:"0254045",limit:1}});
      expect(result.isError).not.toBe(true);
      expect(result.structuredContent).toMatchObject({ total_count:1, medicines:[{sukl_code:"0254045"}], provenance:{source_as_of:expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),source_valid_until:expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)} });
      const combination = await getMedicineByCode("0000009");
      expect(combination?.substance).toContain("ACIDUM ACETYLSALICYLICUM");
      expect(combination?.substance).toContain("COFFEINUM");
      expect(combination?.registration_number).toBeTruthy();
    } finally { await c.close(); }
  });
  it("preserves missing codes and rejects numeric strings, invalid codes and extra arguments", async () => {
    const c = await client();
    try {
      const cards = await c.callTool({name:"display_medicines",arguments:{sukl_codes:["0254045","9999999"]}});
      expect(cards.structuredContent).toMatchObject({missing_codes:["9999999"]});
      for (const args of [{query:"paralen",limit:"10"},{query:"paralen",limit:1000},{query:"paralen",patient_name:"Test"}]) expect((await c.callTool({name:"search_medicines",arguments:args})).isError).toBe(true);
      expect((await c.callTool({name:"get_medicine",arguments:{sukl_code:"../../../etc/passwd"}})).isError).toBe(true);
      expect((await c.callTool({name:"get_medicine",arguments:{sukl_code:"9999999"}})).structuredContent).toMatchObject({status:"not_found",medicine:null});
    } finally { await c.close(); }
  });
  it("returns truthful availability and bounded pharmacy results on the original endpoint", async () => {
    const c = await client(true);
    try {
      const result = await c.callTool({name:"batch-check-availability",arguments:{sukl_codes:["0254045","9999999"]}});
      expect(result.structuredContent).toMatchObject({total_checked:2,unknown_count:1,not_found_count:1,available_count:0,results:[{status:"unknown",last_checked:null},{status:"not_found"}]});
      const pharmacies = await c.callTool({name:"find-pharmacies",arguments:{}});
      const data = pharmacies.structuredContent as {pharmacies:unknown[];total_count:number};
      expect(data.pharmacies).toHaveLength(20); expect(data.total_count).toBeGreaterThan(1000);
      expect((await c.callTool({name:"find-pharmacies",arguments:{is_24h:true}})).isError).toBe(true);
    } finally { await c.close(); }
  });
  it("uses correct ATC levels and totals independent of the search limit", async () => {
    expect(await getATCInfo("N02BE01")).toMatchObject({level:5,parent_code:"N02BE"});
    expect(await getATCInfo("A01")).toMatchObject({level:2,parent_code:"A"});
    expect(await getATCInfo("V06XX")).toMatchObject({parent_code:null});
    const [one,many] = await Promise.all([searchMedicines("paralen",1), searchMedicines("paralen",20)]);
    expect(one.total_count).toBe(many.total_count); expect(one.total_count).toBeGreaterThan(1);
  });
  it("distinguishes missing documents, network failures and bad metadata; sends only padded code", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json([{id:123,typ:"PIL"}])); vi.stubGlobal("fetch",fetchMock);
    const doc = await catalogueOperation("get_medicine_document",{sukl_code:"254045",document_type:"PIL"});
    expect(doc).toMatchObject({status:"ok",document:{url:"https://prehledy.sukl.cz/dlp/v1/dokumenty/123",content_included:false}});
    expect(fetchMock.mock.calls[0][0]).toBe("https://prehledy.sukl.cz/dlp/v1/dokumenty-metadata/0254045");
    fetchMock.mockResolvedValueOnce(Response.json([])); expect(await catalogueOperation("get_medicine_document",{sukl_code:"0254045",document_type:"PIL"})).toMatchObject({status:"document_not_found"});
    fetchMock.mockResolvedValueOnce(new Response(null,{status:503})); await expect(catalogueOperation("get_medicine_document",{sukl_code:"0254045",document_type:"PIL"})).rejects.toThrow();
    fetchMock.mockResolvedValueOnce(Response.json([{id:"https://evil.test",typ:"PIL"}])); await expect(catalogueOperation("get_medicine_document",{sukl_code:"0254045",document_type:"PIL"})).rejects.toThrow();
  });
  it("rejects untrusted origins, malformed envelopes, batches and oversized bodies; GET is 405", async () => {
    expect((await handleCatalogueHttp(new Request(url,{headers:{Origin:"https://evil.test"}}))).status).toBe(403);
    expect((await handleCatalogueHttp(new Request(url))).status).toBe(405);
    for (const body of [null,[],[{jsonrpc:"2.0",id:1,method:"ping"}],{jsonrpc:"1.0",id:1,method:"ping"}]) {
      const res = await handleCatalogueHttp(new Request(url,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json, text/event-stream"},body:JSON.stringify(body)})); expect(res.status).toBe(400);
    }
    const tooBig = await handleCatalogueHttp(new Request(url,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json, text/event-stream"},body:"a".repeat(17000)})); expect(tooBig.status).toBe(413);
    const notification = await handleCatalogueHttp(new Request(url,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json, text/event-stream"},body:JSON.stringify({jsonrpc:"2.0",method:"notifications/initialized"})})); expect(notification.status).toBe(202);
  });
});
