import { describe, it, expect, vi, afterEach } from "vitest";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { GET } from "@/app/.well-known/openai-apps-challenge/route";
import { CHATGPT_TOOLS } from "@/lib/chatgpt-mcp";
import { catalogueOperation } from "@/lib/chatgpt-catalogue";
import { privacyPage, pluginPage } from "@/lib/publication-pages";

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });
describe("Public plugin contracts", () => {
  it("validates representative and absent records against every advertised output schema", async () => {
    const ajv = new Ajv2020({strict:false}); addFormats(ajv);
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => Response.json([{id:123,typ:"PIL"}])));
    const cases = [
      ["search_medicines",{query:"0254045",limit:1}], ["search_medicines",{query:"zzzznonexistentzzzz"}],
      ["get_medicine",{sukl_code:"0254045"}], ["get_medicine",{sukl_code:"9999999"}],
      ["get_atc_group",{atc_code:"N02BE01",limit:2}], ["get_atc_group",{atc_code:"Z99ZZ99"}],
      ["get_medicine_document",{sukl_code:"0254045",document_type:"PIL"}],
      ["get_medicine_document",{sukl_code:"0254045",document_type:"SPC"}],
      ["get_medicine_document",{sukl_code:"9999999",document_type:"PIL"}],
      ["display_medicines",{sukl_codes:["0254045","9999999"]}],
    ] as const;
    for (const [name,args] of cases) {
      const schema = CHATGPT_TOOLS.find(t => t.name === name)!.outputSchema!;
      const data = await catalogueOperation(name,args);
      expect(ajv.validate(schema,data), `${name}: ${JSON.stringify(ajv.errors)}`).toBe(true);
      expect(data.provenance).toMatchObject({source_name:"SÚKL",terms_url:"https://opendata.sukl.gov.cz/?q=podminky-uziti-otevrenych-dat"});
    }
    const schema = CHATGPT_TOOLS.find(t => t.name === "get_medicine")!.outputSchema!;
    expect(ajv.validate(schema,{status:"ok",provenance:{},medicine:{sukl_code:"123"}})).toBe(false);
  });
  it("limits UI tool access to rendering and official document links", () => {
    for (const tool of CHATGPT_TOOLS) {
      const meta = tool._meta?.ui as {visibility:string[];resourceUri?:string};
      expect(meta.visibility).toEqual(["get_medicine_document","display_medicines"].includes(tool.name) ? ["model","app"] : ["model"]);
      expect(Boolean(meta.resourceUri)).toBe(tool.name === "display_medicines");
    }
  });
  it("serves only the exact issued domain token and does not advertise a placeholder", async () => {
    for (const value of ["", " synthetic", "synthetic\nsecond-token"]) { vi.stubEnv("OPENAI_APPS_CHALLENGE",value); expect(GET().status).toBe(404); }
    vi.stubEnv("OPENAI_APPS_CHALLENGE","synthetic-public-challenge"); const response = GET();
    expect(response.status).toBe(200); expect(response.headers.get("Content-Type")).toContain("text/plain");
    expect(await response.text()).toBe("synthetic-public-challenge");
  });
  it("attributes SÚKL data separately from the software license while keeping privacy drafts gated", async () => {
    vi.stubEnv("PUBLICATION_POLICY_CONFIRMED","false");
    expect(privacyPage().status).toBe(503);
    expect(await pluginPage().text()).toContain("https://opendata.sukl.gov.cz/?q=podminky-uziti-otevrenych-dat");
  });
});
