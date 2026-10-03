import { describe, it, expect } from "vitest";
import { handleJsonRpc } from "@/lib/mcp-handler";

describe("MCP Full Flow Integration", () => {
  it("initialize → tools/list → search-medicine", async () => {
    // 1. Initialize
    const init = await handleJsonRpc({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-03-26",
        capabilities: {},
        clientInfo: { name: "integration-test", version: "1.0" },
      },
    });
    expect(init!.result).toHaveProperty("serverInfo");

    // 2. List tools
    const list = await handleJsonRpc({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/list",
      params: {},
    });
    const tools = (list!.result as { tools: { name: string }[] }).tools;
    expect(tools.length).toBe(9);
    expect(tools.map((t) => t.name)).toContain("search-medicine");

    // 3. Search
    const search = await handleJsonRpc({
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "search-medicine",
        arguments: { query: "paralen", limit: 5 },
      },
    });
    const content = (search!.result as { content: { text: string }[] }).content;
    const data = JSON.parse(content[0].text);
    expect(data).toHaveProperty("medicines");
    expect(data.medicines.length).toBeGreaterThan(0);
  });

  it("get-reimbursement returns real data", async () => {
    const result = await handleJsonRpc({
      jsonrpc: "2.0",
      id: 10,
      method: "tools/call",
      params: {
        name: "get-reimbursement",
        arguments: { sukl_code: "0094156" },
      },
    });
    const content = (result!.result as { content: { text: string }[] }).content;
    const data = JSON.parse(content[0].text);
    expect(data.reimbursement_group).toBeNull();
    expect(data.reimbursement_conditions).toBe("ATB");
    expect(data.valid_from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(data.max_price).toBeGreaterThan(0);
  });

  it("find-pharmacies returns results for Praha", async () => {
    const result = await handleJsonRpc({
      jsonrpc: "2.0",
      id: 11,
      method: "tools/call",
      params: {
        name: "find-pharmacies",
        arguments: { city: "Praha" },
      },
    });
    const content = (result!.result as { content: { text: string }[] }).content;
    const data = JSON.parse(content[0].text);
    expect(data.pharmacies.length).toBeGreaterThan(0);
    expect(data.pharmacies.length).toBeLessThanOrEqual(20);
    expect(data.pharmacies[0].city).toBe("Praha");
  });
});
