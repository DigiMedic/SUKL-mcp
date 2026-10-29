import { catalogueOperation } from "@/lib/chatgpt-catalogue";
export async function GET() {
  if (process.env.NODE_ENV === "production") return new Response(null, { status: 404 });
  return Response.json(await catalogueOperation("display_medicines", { sukl_codes: ["0254045", "0000009"] }));
}
