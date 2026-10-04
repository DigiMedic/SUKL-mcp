/**
 * MCP JSON-RPC 2.0 Handler
 * Implements Streamable HTTP transport for Model Context Protocol
 */

import {
  searchMedicines,
  getMedicineByCode,
  getReimbursement,
  getDocumentContent,
  checkAvailability,
  findPharmacies,
  getATCInfo,
  getMedicinesByATC,
  getCatalogueProvenance,
} from "./sukl-client";

// ============================================================================
// JSON-RPC Types
// ============================================================================

interface JsonRpcRequest {
  jsonrpc: "2.0";
  id?: string | number;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

// ============================================================================
// Tool Definitions
// ============================================================================

const TOOLS = [
  {
    name: "search-medicine",
    description:
      "Vyhledávání léčiv v české databázi SÚKL. Podporuje fuzzy vyhledávání podle názvu léku, účinné látky nebo SÚKL kódu.",
    inputSchema: {
      type: "object" as const,
      properties: {
        query: {
          type: "string",
          description: "Vyhledávací dotaz — název léku, účinná látka nebo SÚKL kód (min. 2 znaky)",
        },
        limit: {
          type: "integer",
          minimum: 1, maximum: 100,
          description: "Maximální počet výsledků (výchozí: 20, rozsah: 1–100)",
          default: 20,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "get-medicine-details",
    description:
      "Získání detailních informací o léčivém přípravku podle SÚKL kódu. Vrací dostupné katalogové údaje a datum snímku; neznámé hodnoty jsou null.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_code: {
          type: "string",
          description: "SÚKL kód léku (např. '0254045')",
        },
      },
      required: ["sukl_code"],
    },
  },
  {
    name: "check-availability",
    description:
      "Vrátí unknown: skutečná skladová dostupnost není v tomto serveru ověřována. Registrace přípravku neznamená jeho dostupnost.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_code: {
          type: "string",
          description: "SÚKL kód léku ke kontrole",
        },
      },
      required: ["sukl_code"],
    },
  },
  {
    name: "find-pharmacies",
    description:
      "Vyhledání lékáren v České republice. Filtrování podle města nebo PSČ, s omezením výsledků. Nepřetržitý provoz není ověřen.",
    inputSchema: {
      type: "object" as const,
      properties: {
        limit: { type: "integer", minimum: 1, maximum: 100, default: 20 },
        offset: { type: "integer", minimum: 0, maximum: 10000, default: 0 },
        city: {
          type: "string",
          description: "Název města (např. 'Praha', 'Brno')",
        },
        postal_code: {
          type: "string",
          description: "PSČ nebo jeho prefix (např. '110' pro Prahu 1)",
        },
        is_24h: {
          type: "boolean",
          description: "Filtrovat pouze lékárny s nepřetržitým provozem",
        },
      },
    },
  },
  {
    name: "get-atc-info",
    description:
      "Informace o ATC (Anatomicko-terapeuticko-chemická) klasifikaci léčiv. ATC systém kategorizuje léčiva podle terapeutického využití.",
    inputSchema: {
      type: "object" as const,
      properties: {
        atc_code: {
          type: "string",
          description: "ATC kód (např. 'N02BE01' pro paracetamol, 'C' pro kardiovaskulární)",
        },
        include_medicines: {
          type: "boolean",
          description: "Zahrnout seznam léčiv v dané ATC skupině (výchozí: false)",
          default: false,
        },
        medicines_limit: {
          type: "integer",
          minimum: 1, maximum: 100,
          description: "Maximální počet léčiv v seznamu (výchozí: 20)",
          default: 20,
        },
      },
      required: ["atc_code"],
    },
  },
  {
    name: "get-reimbursement",
    description:
      "Informace o úhradě a cenách léčivého přípravku. Vrací MFC, úhradu UHR1, vypočtený maximální doplatek a preskripční omezení ze SCAU s datem platnosti. Skutečná prodejní cena a nárok na úhradu se mohou lišit.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_code: {
          type: "string",
          description: "SÚKL kód léku",
        },
      },
      required: ["sukl_code"],
    },
  },
  {
    name: "get-pil-content",
    description:
      "Příbalový leták (PIL) léčivého přípravku. Vrací metadata a URL ke stažení PDF dokumentu ze SÚKL. Obsah PDF není součástí odpovědi.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_code: {
          type: "string",
          description: "SÚKL kód léku",
        },
      },
      required: ["sukl_code"],
    },
  },
  {
    name: "get-spc-content",
    description:
      "Souhrn údajů o přípravku (SPC/SmPC). Vrací metadata a URL ke stažení PDF dokumentu ze SÚKL. Obsah PDF není součástí odpovědi.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_code: {
          type: "string",
          description: "SÚKL kód léku",
        },
      },
      required: ["sukl_code"],
    },
  },
  {
    name: "batch-check-availability",
    description:
      "Vrátí unknown pro známé přípravky a not_found pro neznámé kódy. Skladovou dostupnost server neověřuje.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sukl_codes: {
          type: "array",
          items: { type: "string" },
          description: "Pole SÚKL kódů ke kontrole (max 50)",
        },
      },
      required: ["sukl_codes"],
    },
  },
].map(tool => ({ ...tool, annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true, idempotentHint: true }, _meta: { securitySchemes: [{ type: "noauth" }] } }));

// ============================================================================
// Server Info
// ============================================================================

const SERVER_INFO = {
  name: "sukl-mcp",
  version: "6.0.2",
  description:
    "MCP server pro českou databázi léčivých přípravků SÚKL (~68k léků)",
};

// ============================================================================
// Tool Execution
// ============================================================================

class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

function validateString(value: unknown, name: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new ValidationError(`Parametr '${name}' musí být neprázdný řetězec.`);
  }
  return value.trim();
}

function validateArray(value: unknown, name: string, maxItems: number): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new ValidationError(`Parametr '${name}' musí být neprázdné pole řetězců.`);
  }
  if (value.length > maxItems) {
    throw new ValidationError(`Maximální počet položek v '${name}' je ${maxItems}.`);
  }
  return value.map((item, i) => {
    if (typeof item !== "string" || !/^\d{1,7}$/.test(item)) {
      throw new ValidationError(`Položka ${i + 1} v '${name}' musí být neprázdný řetězec.`);
    }
    return item.trim();
  });
}

function validateNumber(value: unknown, fallback: number, min: number, max: number): number {
  if (value === undefined) return fallback;
  if (typeof value !== "number" || !Number.isInteger(value) || value < min || value > max) throw new ValidationError(`Číselný parametr musí být celé číslo ${min}–${max}.`);
  return value;
}
function validateCode(value: unknown): string {
  const code = validateString(value, "sukl_code");
  if (!/^\d{1,7}$/.test(code)) throw new ValidationError("Neplatný kód SÚKL.");
  return code;
}
type ToolResponse = { content: { type: "text"; text: string }[]; isError?: boolean; structuredContent?: Record<string, unknown> };

function textResponse(text: string): ToolResponse {
  return { content: [{ type: "text", text }] };
}

export async function executeTool(
  name: string,
  args: Record<string, unknown>
): Promise<ToolResponse> {
  const startTime = performance.now();
  try {
    const definition = TOOLS.find(tool => tool.name === name);
    if (definition && Object.keys(args).some(key => !(key in (definition.inputSchema.properties ?? {})))) throw new ValidationError("Nepovolený parametr.");
    let result: unknown;

    switch (name) {
      case "search-medicine": {
        const query = validateString(args.query, "query");
        if (query.length > 200) {
          throw new ValidationError("Vyhledávací dotaz nesmí překročit 200 znaků.");
        }
        const limit = validateNumber(args.limit, 20, 1, 100);
        result = await searchMedicines(query, limit);
        break;
      }
      case "get-medicine-details": {
        const code = validateCode(args.sukl_code);
        result = await getMedicineByCode(code);
        if (!result) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`Lék s SÚKL kódem '${code}' nebyl nalezen.`));
        }
        break;
      }
      case "check-availability": {
        const code = validateCode(args.sukl_code);
        result = await checkAvailability(code);
        if (!result) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`Lék s SÚKL kódem '${code}' nebyl nalezen.`));
        }
        break;
      }
      case "find-pharmacies": {
        if (args.is_24h !== undefined) throw new ValidationError("Nepřetržitý provoz není ověřen; filtr is_24h není podporován.");
        const city = args.city === undefined ? undefined : validateString(args.city, "city");
        const postal = args.postal_code === undefined ? undefined : validateString(args.postal_code, "postal_code");
        if ((city && city.length > 100) || (postal && !/^\d{1,5}$/.test(postal))) throw new ValidationError("Neplatný filtr lékáren.");
        const pharmacies = await findPharmacies(city, postal);
        const limit = validateNumber(args.limit, 20, 1, 100);
        const offset = validateNumber(args.offset, 0, 0, 10000);
        result = { pharmacies: pharmacies.slice(offset, offset + limit), total_count: pharmacies.length, offset, limit };
        break;
      }
      case "get-atc-info": {
        const atcCode = validateString(args.atc_code, "atc_code").toUpperCase();
        if (!/^(?:[A-Z]|[A-Z]\d{2}|[A-Z]\d{2}[A-Z]|[A-Z]\d{2}[A-Z]{2}|[A-Z]\d{2}[A-Z]{2}\d{2})$/.test(atcCode)) throw new ValidationError("Neplatný kód ATC.");
        if (args.include_medicines !== undefined && typeof args.include_medicines !== "boolean") throw new ValidationError("include_medicines musí být boolean.");
        const includeMedicines = args.include_medicines === true;
        const medicinesLimit = validateNumber(args.medicines_limit, 20, 1, 100);

        const atcInfo = await getATCInfo(atcCode);
        if (!atcInfo) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`ATC kód '${atcCode}' nebyl nalezen.`));
        }

        if (includeMedicines) {
          const medicines = await getMedicinesByATC(atcCode);
          result = {
            ...atcInfo,
            medicines: medicines.slice(0, medicinesLimit),
            medicines_total: medicines.length,
          };
        } else {
          result = atcInfo;
        }
        break;
      }
      case "get-reimbursement": {
        const code = validateCode(args.sukl_code);
        result = await getReimbursement(code);
        if (!result) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`Informace o úhradě pro SÚKL kód '${code}' nejsou k dispozici.`));
        }
        break;
      }
      case "get-pil-content": {
        const code = validateCode(args.sukl_code);
        const document = await getDocumentContent(code, "PIL");
        if (document && !document.document_url) return { ...textResponse(document.content), isError: true };
        result = document;
        if (!result) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`Příbalový leták pro SÚKL kód '${code}' nebyl nalezen.`));
        }
        break;
      }
      case "get-spc-content": {
        const code = validateCode(args.sukl_code);
        const document = await getDocumentContent(code, "SPC");
        if (document && !document.document_url) return { ...textResponse(document.content), isError: true };
        result = document;
        if (!result) {
          return logAndReturn(name, args, startTime, "ok",
            textResponse(`SPC pro SÚKL kód '${code}' nebylo nalezeno.`));
        }
        break;
      }
      case "batch-check-availability": {
        const codes = validateArray(args.sukl_codes, "sukl_codes", 50);
        const results = await Promise.all(
          codes.map((code) => checkAvailability(code))
        );
        const validResults = results.map((r, i) => r ?? { sukl_code: codes[i], status: "not_found" });
        let availableCount = 0;
        let unavailableCount = 0;
        for (const r of validResults) {
          if (r?.status === "available") availableCount++;
          else if (r?.status === "unavailable") unavailableCount++;
        }
        result = {
          results: validResults,
          total_checked: codes.length,
          available_count: availableCount,
          unavailable_count: unavailableCount,
          unknown_count: validResults.filter(r => r.status === "unknown").length,
          not_found_count: validResults.filter(r => r.status === "not_found").length,
        };
        break;
      }
      default:
        return logAndReturn(name, args, startTime, "ok",
          { ...textResponse(`Neznámý nástroj: '${name}'`), isError: true });
    }

    return logAndReturn(name, args, startTime, "ok",
      { ...textResponse(JSON.stringify({ ...(result && typeof result === "object" && !Array.isArray(result) ? result : { data: result }), provenance: getCatalogueProvenance() })), structuredContent: { ...(result && typeof result === "object" && !Array.isArray(result) ? result : { data: result }), provenance: getCatalogueProvenance() } });
  } catch (error) {
    const duration_ms = Math.round(performance.now() - startTime);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.log(JSON.stringify({
      event: "mcp_tool_call",
      tool: name,
      duration_ms,
      status: "error",
      error: errorMessage,
    }));
    return { ...textResponse(error instanceof ValidationError ? errorMessage : "Chyba při zpracování požadavku. Zkuste to znovu."), isError: true };
  }
}

function logAndReturn(
  tool: string,
  params: Record<string, unknown>,
  startTime: number,
  status: "ok" | "error",
  response: ToolResponse,
): ToolResponse {
  const duration_ms = Math.round(performance.now() - startTime);
  console.log(JSON.stringify({
    event: "mcp_tool_call",
    tool,
    duration_ms,
    status,
  }));
  return response;
}

// ============================================================================
// JSON-RPC Handler
// ============================================================================

export async function handleJsonRpc(
  request: JsonRpcRequest
): Promise<JsonRpcResponse | null> {
  if (!request || typeof request !== "object" || Array.isArray(request) || request.jsonrpc !== "2.0" || typeof request.method !== "string" || (request.id !== undefined && typeof request.id !== "string" && typeof request.id !== "number") || (request.params !== undefined && (!request.params || typeof request.params !== "object" || Array.isArray(request.params)))) {
    return { jsonrpc: "2.0", id: null, error: { code: -32600, message: "Invalid Request" } };
  }
  const { method, params, id } = request;

  // Notifications (no id) — return null to signal 202 response
  if (id === undefined || id === null) {
    return null;
  }

  switch (method) {
    case "initialize":
      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2025-03-26",
          capabilities: {
            tools: { listChanged: false },
          },
          serverInfo: SERVER_INFO,
        },
      };

    case "ping":
      return {
        jsonrpc: "2.0",
        id,
        result: {},
      };

    case "tools/list":
      return {
        jsonrpc: "2.0",
        id,
        result: { tools: TOOLS },
      };

    case "tools/call": {
      const toolName = (params as Record<string, unknown>)?.name as string;
      const toolArgs =
        ((params as Record<string, unknown>)?.arguments as Record<
          string,
          unknown
        >) || {};

      if (!toolName) {
        return {
          jsonrpc: "2.0",
          id,
          error: {
            code: -32602,
            message: "Invalid params: missing tool name",
          },
        };
      }

      const toolResult = await executeTool(toolName, toolArgs);
      return {
        jsonrpc: "2.0",
        id,
        result: toolResult,
      };
    }

    default:
      return {
        jsonrpc: "2.0",
        id,
        error: {
          code: -32601,
          message: `Method not found: ${method}`,
        },
      };
  }
}

export { SERVER_INFO, TOOLS };
