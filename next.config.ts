import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig: NextConfig = {
  agentRules: false,
  turbopack: { root: process.cwd() },
  outputFileTracingIncludes: {
    "/api/mcp": ["./data/bundled-data.json"],
    "/api/chatgpt/mcp": ["./data/bundled-data.json", "./widgets/dist/medicines.html"],
  },
  async rewrites() { return [{ source: "/mcp", destination: "/api/mcp" }, { source: "/chatgpt/mcp", destination: "/api/chatgpt/mcp" }]; },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Content-Security-Policy",
            value: `default-src 'self'; script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'${process.env.NODE_ENV === "development" ? " ws: wss:" : ""}; frame-ancestors 'none'`,
          },
        ],
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
