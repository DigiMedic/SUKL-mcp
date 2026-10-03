import { handleCatalogueHttp } from "@/lib/chatgpt-mcp";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const handle = (request: Request) => handleCatalogueHttp(request);
export const POST = handle;
export const GET = handle;
export const DELETE = handle;
export const OPTIONS = handle;
