import { readFileSync } from "node:fs";
export async function GET() {
  if (process.env.NODE_ENV === "production") return new Response(null, { status: 404 });
  return new Response(readFileSync("widgets/dist/preview.html", "utf8"), { headers: { "Content-Type": "text/html; charset=utf-8" } });
}
