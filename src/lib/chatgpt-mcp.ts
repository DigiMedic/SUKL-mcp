import { allowMcpRequest } from "./shared-rate-limit";
import { readObject, HttpInputError } from "./http-input";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { CallToolRequestSchema, ListToolsRequestSchema, ListResourcesRequestSchema, ReadResourceRequestSchema, McpError, ErrorCode, type Tool } from "@modelcontextprotocol/sdk/types.js";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { CatalogueInputError, catalogueOperation } from "./chatgpt-catalogue";

export const CATALOGUE_UI_URI = "ui://sukl-catalogue/medicines-v1.html";
const code = { type: "string", pattern: "^[0-9]{1,7}$", description: "Veřejný kód přípravku SÚKL, nikoli osobní identifikátor." };
const count = { type: "integer", minimum: 1, maximum: 20, default: 10 };
const annotations = { readOnlyHint: true, destructiveHint: false, openWorldHint: true, idempotentHint: true };
const securitySchemes = [{ type: "noauth" }];
const outputSchema = { type: "object" as const, properties: { status: { type: "string" }, provenance: { type: "object" } }, required: ["status", "provenance"] };

function tool(name: string, title: string, description: string, properties: Record<string, object>, required: string[], ui = false): Tool & { securitySchemes: { type: string }[] } {
  return { name, title, description, inputSchema: { type: "object", properties, required, additionalProperties: false }, outputSchema, annotations, securitySchemes,
    _meta: { securitySchemes, ...(ui ? { ui: { resourceUri: CATALOGUE_UI_URI }, "openai/outputTemplate": CATALOGUE_UI_URI } : {}) } };
}

export const CHATGPT_TOOLS: Tool[] = [
  tool("search_medicines", "Vyhledat léčivé přípravky", "Vyhledá přípravky v českém datovém snímku SÚKL podle názvu, uvedené látky nebo kódu. query obsahuje pouze název/látku/kód, bez zdravotních údajů člověka. Vrací nejvýše 20 výsledků a datum snímku; nelze z nich odvodit aktuální cenu, dostupnost nebo úplné složení kombinace.", { query: { type: "string", minLength: 1, maxLength: 100, description: "Pouze název léčiva, látky nebo kód SÚKL." }, limit: count }, ["query"]),
  tool("get_medicine", "Detail léčivého přípravku", "Vrátí katalogové údaje pro konkrétní kód SÚKL, datum snímku a stav not_found při nenalezení. Registrace není skladová dostupnost. Uvedená látka může být neúplná; složení ověřte v oficiálním dokumentu. Neposkytuje individuální léčebná doporučení.", { sukl_code: code }, ["sukl_code"]),
  tool("get_atc_group", "Klasifikace ATC", "Vrátí ATC skupinu, její úroveň, nadřazený kód a omezený seznam přípravků z datového snímku. Společná klasifikace neznamená zaměnitelnost léčiv. Neznámý kód vrací not_found.", { atc_code: { type: "string", minLength: 1, maxLength: 7 }, limit: count }, ["atc_code"]),
  tool("get_medicine_document", "Odkaz na PIL nebo SPC", "Pro kód SÚKL vyhledá na veřejném API SÚKL odkaz na příbalovou informaci (PIL) nebo souhrn údajů (SPC). Vrací odkaz, nikoli přečtený obsah PDF. Neznámý přípravek a chybějící dokument mají odlišné stavy; nedostupné API vrací chybu. Na SÚKL se odesílá pouze kód přípravku.", { sukl_code: code, document_type: { type: "string", enum: ["PIL", "SPC"] } }, ["sukl_code", "document_type"]),
  tool("display_medicines", "Zobrazit karty léčiv", "Zobrazí přehledné karty 1 až 10 konkrétních přípravků v chatu. Použijte pouze kódy relevantní k požadavku uživatele. Vrací také úplná textová data, datum snímku a seznam nenalezených kódů; funguje i bez podpory grafické aplikace. Nezobrazuje ceny, zásoby ani reklamu.", { sukl_codes: { type: "array", items: code, minItems: 1, maxItems: 10 } }, ["sukl_codes"], true),
];

function validateArguments(definition: Tool, args: Record<string, unknown>) {
  const properties = definition.inputSchema.properties ?? {};
  if (Object.keys(args).some(key => !(key in properties))) throw new CatalogueInputError("Požadavek obsahuje nepovolené parametry.");
  if ((definition.inputSchema.required ?? []).some(key => !(key in args))) throw new CatalogueInputError("Chybí povinný parametr.");
}

export function createCatalogueServer() {
  const server = new Server({ name: "sukl-catalogue", version: "1.0.0" }, {
    capabilities: { tools: {}, resources: {} },
    instructions: "Informační katalog českých léčiv pro konverzaci. Pracujte pouze s názvem léčiva, látkou, ATC nebo kódem SÚKL, nikoli s údaji o pacientovi. Uvádějte datum snímku a jeho omezení. Registrace neznamená dostupnost. Výsledky nejsou osobním léčebným doporučením. Dokumentový nástroj vrací pouze odkaz; netvrďte, že byl obsah PDF přečten. SÚKL MCP je nezávislý projekt, nikoli oficiální aplikace SÚKL.",
  });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: CHATGPT_TOOLS }));
  server.setRequestHandler(CallToolRequestSchema, async request => {
    const definition = CHATGPT_TOOLS.find(t => t.name === request.params.name);
    if (!definition) throw new McpError(ErrorCode.InvalidParams, "Neznámý nástroj.");
    try {
      const args = request.params.arguments ?? {};
      validateArguments(definition, args);
      const structuredContent = await catalogueOperation(definition.name, args);
      return { content: [{ type: "text", text: JSON.stringify(structuredContent) }], structuredContent };
    } catch (error) {
      const message = error instanceof CatalogueInputError ? error.message : "Data nebo dokument SÚKL nyní nelze získat. Zkuste požadavek později.";
      return { content: [{ type: "text", text: message }], isError: true };
    }
  });
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: [{ uri: CATALOGUE_UI_URI, name: "Karty léčiv", mimeType: "text/html;profile=mcp-app" }] }));
  server.setRequestHandler(ReadResourceRequestSchema, async request => {
    if (request.params.uri !== CATALOGUE_UI_URI) throw new McpError(ErrorCode.InvalidParams, "Neznámý prostředek.");
    return { contents: [{ uri: CATALOGUE_UI_URI, mimeType: "text/html;profile=mcp-app", text: readFileSync(join(process.cwd(), "widgets/dist/medicines.html"), "utf8"), _meta: { ui: { prefersBorder: true, domain: process.env.MCP_WIDGET_DOMAIN ?? process.env.MCP_PUBLIC_ORIGIN ?? "https://sukl-mcp.vercel.app", csp: { connectDomains: [], resourceDomains: [] } } } }] };
  });
  return server;
}

export async function handleCatalogueHttp(request: Request, factory = createCatalogueServer): Promise<Response> {
  const origin = request.headers.get("origin");
  const publicOrigin = process.env.MCP_PUBLIC_ORIGIN ?? (process.env.NODE_ENV === "production" ? "https://sukl-mcp.vercel.app" : new URL(request.url).origin);
  const allowedOrigins = new Set([publicOrigin, "https://chatgpt.com", "https://chat.openai.com", ...(process.env.MCP_ALLOWED_ORIGINS ?? "").split(",").filter(Boolean)]);
  if (origin && !allowedOrigins.has(origin)) return new Response("Origin není povolen.", { status: 403 });
  const headers = new Headers({ "Cache-Control": "no-store" });
  if (origin) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Vary", "Origin");
    headers.set("Access-Control-Allow-Methods", "POST, GET, DELETE, OPTIONS");
    headers.set("Access-Control-Allow-Headers", "Content-Type, Accept, MCP-Protocol-Version, Mcp-Session-Id");
  }
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
  if (request.method !== "POST") {
    headers.set("Allow", "POST, OPTIONS");
    return new Response("Samostatný SSE stream a serverové relace nejsou podporovány.", { status: 405, headers });
  }
  const ip = process.env.VERCEL ? request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown" : "local";
  try { if (!await allowMcpRequest(ip)) return new Response("Překročen limit požadavků.", { status: 429, headers: { "Retry-After": "60" } }); }
  catch { return new Response("Služba nyní nemůže bezpečně přijímat požadavky.", { status: 503 }); }
  let parsedBody: Record<string, unknown>;
  try { parsedBody = await readObject(request); }
  catch (error) {
    const status = error instanceof HttpInputError ? error.status : 400;
    return Response.json({ jsonrpc: "2.0", id: null, error: { code: error instanceof HttpInputError ? error.rpcCode : -32600, message: error instanceof HttpInputError ? error.message : "Neplatný požadavek." } }, { status, headers });
  }
  const server = factory();
  const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true, maxRequestBodySize: 16 * 1024 });
  try {
    await server.connect(transport);
    const response = await transport.handleRequest(request, { parsedBody });
    for (const [key, value] of headers) response.headers.set(key, value);
    return response;
  } finally {
    await server.close();
  }
}
