import type { Metadata } from "next";
import { Inter, JetBrains_Mono, VT323 } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

const vt323 = VT323({
  weight: "400",
  subsets: ["latin", "latin-ext"],
  variable: "--font-mono-display",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://sukl-mcp.vercel.app"),
  title: "SÚKL MCP | České léky pro AI agenty",
  description:
    "Přístup ke katalogu léčiv SÚKL přímo z ChatGPT, Claude nebo tvého AI agenta. Open source MCP server pro českou databázi léků.",
  keywords: [
    "SÚKL",
    "MCP",
    "Claude",
    "AI",
    "léky",
    "databáze léčiv",
    "healthcare AI",
    "Czech drugs",
    "příbalový leták",
    "SPC",
    "lékárna",
  ],
  authors: [{ name: "Petr Sovadina" }],
  creator: "Petr Sovadina",
  publisher: "Petr Sovadina",
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    title: "SÚKL MCP | České léky pro AI agenty",
    description:
      "68k+ léků • 9 tools • Open Source. Přístup k SÚKL databázi přímo z tvého AI agenta.",
    url: "https://sukl-mcp.vercel.app",
    siteName: "SÚKL MCP",
    locale: "cs_CZ",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "SÚKL MCP - České léky pro AI agenty",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SÚKL MCP | České léky pro AI agenty",
    description:
      "68k+ léků • 9 tools • Open Source. MCP server pro českou databázi léčiv.",
    images: ["/og-image.png"],
  },
  alternates: {
    canonical: "https://sukl-mcp.vercel.app",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="cs" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${vt323.variable} font-sans antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem={false}
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
        {process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === "true" ? <Analytics /> : null}
      </body>
    </html>
  );
}
