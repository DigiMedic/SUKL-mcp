import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CallToolRequestSchema, ListToolsRequestSchema, McpError, ErrorCode } from "@modelcontextprotocol/sdk/types.js";
import { executeTool, TOOLS, SERVER_INFO } from "./mcp-handler";
export function createLegacyServer() {
  const server = new Server(SERVER_INFO, { capabilities: { tools: {} } });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
  server.setRequestHandler(CallToolRequestSchema, async request => {
    if (!TOOLS.some(tool => tool.name === request.params.name)) throw new McpError(ErrorCode.InvalidParams, "Neznámý nástroj.");
    return executeTool(request.params.name, request.params.arguments ?? {});
  });
  return server;
}
