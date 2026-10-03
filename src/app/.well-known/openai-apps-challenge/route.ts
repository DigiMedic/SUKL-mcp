export function GET() {
  const token = process.env.OPENAI_APPS_CHALLENGE;
  if (!token || token.trim() !== token || /[\r\n]/.test(token)) return new Response(null, { status: 404 });
  return new Response(token, { headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}
