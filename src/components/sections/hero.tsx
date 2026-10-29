"use client";
import catalogueSummary from "../../../data/catalogue-summary.json";

import { motion } from "framer-motion";
import { ArrowRight, Play, Building2, RefreshCw, Zap } from "lucide-react";
import Link from "next/link";
import { TextGenerateEffect } from "@/components/ui/text-generate";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { NumberTicker } from "@/components/ui/number-ticker";
import { PillIcon } from "@/components/icons";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
      {/* Pixel decoration - SÚKL blue tones */}
      <div className="absolute top-20 right-0 w-32 h-32 opacity-20">
        <div className="grid grid-cols-4 gap-1">
          {Array.from({ length: 16 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-6 h-6 rounded-sm"
              style={{
                backgroundColor: ["#1a365d", "#2b6cb0", "#63b3ed"][i % 3],
              }}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: Math.random() * 0.5 + 0.2, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
            />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 text-center relative z-10">
        {/* Badge - What is this */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-pink/10 border border-pink/20 mb-8"
        >
          <PillIcon className="w-5 h-5 text-pink" />
          <span className="text-sm font-medium text-pink">Open Source API pro české léky</span>
        </motion.div>

        {/* Headline - Clear value */}
        <TextGenerateEffect
          words="Kompletní databáze léků v ČR. Pro tvůj software."
          className="font-[family-name:var(--font-mono-display)] text-3xl md:text-5xl lg:text-6xl text-foreground dark:text-foreground mb-6"
        />

        {/* Stats - Concrete numbers */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex flex-wrap justify-center gap-4 md:gap-8 mb-6"
        >
          <StatBadge>
            <NumberTicker value={catalogueSummary.medicine_count} className="text-pink font-bold" />
            <span className="text-muted-foreground">léků v databázi</span>
          </StatBadge>
          <StatBadge>
            <span className="text-pixel-blue font-bold">9</span>
            <span className="text-muted-foreground">API endpointů</span>
          </StatBadge>
          <StatBadge>
            <span className="text-teal font-bold">0 Kč</span>
            <span className="text-muted-foreground">navždy zdarma</span>
          </StatBadge>
        </motion.div>

        {/* Subheadline - Who is this for */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1 }}
          className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-4"
        >
          Vyhledávání léků, kontrola interakcí, příbalové letáky.{" "}
          <span className="text-foreground font-semibold">Jedno API</span> pro{" "}
          <span className="text-foreground font-semibold">zdravotnické aplikace, chatboty a výzkum</span>.
        </motion.p>

        {/* Trust badges - Why trust us */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
          className="flex flex-wrap justify-center gap-3 mb-10 text-sm"
        >
          <span className="px-3 py-1 rounded-full bg-card border border-border text-muted-foreground inline-flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5" />
            Data přímo ze SÚKL
          </span>
          <span className="px-3 py-1 rounded-full bg-card border border-border text-muted-foreground inline-flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" />
            Aktualizováno denně
          </span>
          <span className="px-3 py-1 rounded-full bg-card border border-border text-muted-foreground inline-flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" />
            Odpověď do 100ms
          </span>
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.2 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <ShimmerButton
            href="#quickstart"
            className="text-base"
            shimmerColor="#2b6cb0"
          >
            Začít používat zdarma
            <ArrowRight className="w-4 h-4" />
          </ShimmerButton>

          <Link
            href="https://github.com/petrsovadina/sukl-mcp"
            target="_blank"
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-lg border-2 border-border hover:border-pink hover:bg-pink/5 transition-colors text-foreground font-medium"
          >
            <Play className="w-4 h-4" />
            Dokumentace na GitHubu
          </Link>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-6 h-10 rounded-full border-2 border-border flex justify-center pt-2"
          >
            <div className="w-1.5 h-3 rounded-full bg-pink" />
          </motion.div>
        </motion.div>
      </div>

      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-pink/5 via-transparent to-transparent pointer-events-none" />
    </section>
  );
}

function StatBadge({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-card border border-border shadow-sm">
      {children}
    </div>
  );
}
