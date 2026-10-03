"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, ArrowRight, Sparkles, Building2, Bell, Rocket } from "lucide-react";
import { ContactModal } from "@/components/forms/contact-modal";
import { RegisterModal } from "@/components/forms/register-modal";
import { trackEvent } from "@/lib/analytics";

interface PricingTier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  highlighted?: boolean;
  badge?: string;
  action: "free" | "early-access" | "notify";
  comingSoon?: boolean;
}

const tiers: PricingTier[] = [
  {
    name: "Open Source",
    price: "Zdarma",
    period: "navždy",
    description: "Veřejný katalog z dat SÚKL s limitem požadavků",
    features: [
      "9 MCP nástrojů",
      "Katalogový snímek s uvedenou platností",
      "Ověřované aktualizace dat",
      "Komunitní podpora",
      "MIT licence — open source",
    ],
    cta: "Začít zdarma",
    action: "free",
  },
  {
    name: "Pro",
    price: "Připravujeme",
    period: "",
    description: "Pro firmy a produkční nasazení",
    features: [
      "Vše z Open Source",
      "Vyšší limity požadavků",
      "API klíč + dashboard",
      "Týdenní aktualizace dat",
      "Prioritní podpora",
      "SLA garance",
    ],
    cta: "Získat early access",
    highlighted: true,
    badge: "Brzy",
    action: "early-access",
    comingSoon: true,
  },
  {
    name: "Enterprise",
    price: "Na míru",
    period: "",
    description: "Pro nemocnice, řetězce a velké organizace",
    features: [
      "Vše z Pro",
      "Neomezené požadavky",
      "Denní aktualizace dat",
      "Webhooky pro monitoring",
      "Dedikovaná podpora",
      "Custom SLA",
    ],
    cta: "Chci vědět více",
    action: "notify",
    comingSoon: true,
  },
];

export function Pricing() {
  const [earlyAccessOpen, setEarlyAccessOpen] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);

  function handleAction(action: PricingTier["action"]) {
    trackEvent("pricing_cta", { tier: action });
    switch (action) {
      case "free":
        document.getElementById("quickstart")?.scrollIntoView({ behavior: "smooth" });
        break;
      case "notify":
        setContactOpen(true);
        break;
      case "early-access":
        setEarlyAccessOpen(true);
        break;
    }
  }

  return (
    <section id="pricing" className="py-24 relative">
      <div className="container mx-auto px-4">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-[family-name:var(--font-mono-display)] text-3xl md:text-4xl text-foreground mb-4 tracking-tight">
            Začněte zdarma, rostěte s námi
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Projekt je v rané fázi — open source verze poskytuje katalogové údaje.
            Placené plány připravujeme pro ty, kdo chtějí víc.
          </p>
        </motion.div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {tiers.map((tier, index) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
              className={`relative rounded-2xl p-6 flex flex-col ${
                tier.highlighted
                  ? "bg-card border-2 border-pink shadow-lg shadow-pink/10 scale-[1.02]"
                  : "bg-card border border-border"
              } ${tier.comingSoon ? "opacity-90" : ""}`}
            >
              {/* Badge */}
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-pink text-white text-xs font-medium">
                    <Sparkles className="w-3 h-3" />
                    {tier.badge}
                  </span>
                </div>
              )}

              {/* Header */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  {tier.action === "notify" ? (
                    <Building2 className="w-5 h-5 text-pixel-blue" />
                  ) : tier.action === "free" ? (
                    <Rocket className="w-5 h-5 text-teal" />
                  ) : null}
                  <h3 className="text-lg font-semibold text-foreground">{tier.name}</h3>
                </div>

                <div className="flex items-baseline gap-1 mb-2">
                  <span className={`text-3xl font-bold ${tier.highlighted ? "text-pink" : "text-foreground"}`}>
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className="text-muted-foreground text-sm">{tier.period}</span>
                  )}
                </div>

                <p className="text-muted-foreground text-sm">{tier.description}</p>
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className={`w-4 h-4 mt-0.5 shrink-0 ${
                      tier.comingSoon ? "text-muted-foreground" : tier.highlighted ? "text-pink" : "text-teal"
                    }`} />
                    <span className={tier.comingSoon ? "text-muted-foreground" : "text-foreground"}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                onClick={() => handleAction(tier.action)}
                className={`w-full py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                  tier.highlighted
                    ? "bg-pink text-white hover:bg-pink/90"
                    : tier.comingSoon
                      ? "border-2 border-border text-muted-foreground hover:border-pink hover:text-foreground hover:bg-pink/5"
                      : "border-2 border-border text-foreground hover:border-pink hover:bg-pink/5"
                }`}
              >
                {tier.comingSoon && <Bell className="w-4 h-4" />}
                {tier.cta}
                {!tier.comingSoon && <ArrowRight className="w-4 h-4" />}
              </button>
            </motion.div>
          ))}
        </div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          viewport={{ once: true }}
          className="text-center text-sm text-muted-foreground mt-8"
        >
          Open source katalog zůstává zdarma.
          Zanechte kontakt a budete první, kdo se dozví o nových plánech.
        </motion.p>
      </div>

      {/* Early Access Modal — reuses RegisterModal */}
      <ContactModal isOpen={contactOpen} onClose={() => setContactOpen(false)} />
      <RegisterModal isOpen={earlyAccessOpen} onClose={() => setEarlyAccessOpen(false)} />
    </section>
  );
}
