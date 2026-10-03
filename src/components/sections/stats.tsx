"use client";
import catalogueSummary from "../../../data/catalogue-summary.json";

import { motion } from "framer-motion";
import { NumberTicker } from "@/components/ui/number-ticker";
import { PillIcon, HospitalIcon, BoltIcon } from "@/components/icons";
import { Wrench } from "lucide-react";

const stats = [
  {
    value: catalogueSummary.medicine_count,
    label: "léků v databázi",
    color: "pink",
    icon: <PillIcon className="w-10 h-10" />,
  },
  {
    value: catalogueSummary.pharmacy_count,
    label: "lékáren v ČR",
    color: "pixel-blue",
    icon: <HospitalIcon className="w-10 h-10" />,
  },
  {
    value: 9,
    label: "MCP tools",
    color: "teal",
    icon: <Wrench className="w-10 h-10" />,
  },
  {
    value: 30,
    suffix: "s",
    label: "setup time",
    color: "pink",
    icon: <BoltIcon className="w-10 h-10" />,
  },
];

export function Stats() {
  return (
    <section className="py-24 relative">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className={`text-${stat.color} mb-3 flex justify-center`}>{stat.icon}</div>
              <div className="text-3xl md:text-4xl font-bold mb-2">
                <NumberTicker
                  value={stat.value}
                  className={`text-${stat.color}`}
                  delay={0.5}
                />
                {stat.suffix && (
                  <span className={`text-${stat.color}`}>{stat.suffix}</span>
                )}
              </div>
              <div className="text-muted-foreground text-sm">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Background decoration */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-dark-border to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-dark-border to-transparent" />
    </section>
  );
}
