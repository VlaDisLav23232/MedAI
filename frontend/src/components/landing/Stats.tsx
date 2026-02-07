"use client";

import React from "react";

const stats = [
  {
    value: "87.7%",
    label: "MedQA Accuracy",
    sublabel: "MedGemma 27B Text",
    color: "text-brand-500",
  },
  {
    value: "88.9",
    label: "CXR Macro-F1",
    sublabel: "MedGemma 4B",
    color: "text-accent-cyan",
  },
  {
    value: "56.2%",
    label: "AgentClinic Score",
    sublabel: "Surpasses physicians",
    color: "text-accent-emerald",
  },
  {
    value: "500×",
    label: "Less Compute",
    sublabel: "vs largest competitors",
    color: "text-accent-violet",
  },
  {
    value: "12→2",
    label: "Min per Patient",
    sublabel: "Documentation time",
    color: "text-accent-amber",
  },
  {
    value: "100%",
    label: "Explainable",
    sublabel: "Every output traceable",
    color: "text-accent-rose",
  },
];

export function Stats() {
  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-500 uppercase tracking-wider mb-3">
            Performance
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Built on Proven Benchmarks
          </h2>
          <p className="max-w-2xl mx-auto text-gray-600 dark:text-gray-400">
            Powered by Google&apos;s MedGemma model family — fine-tuned for
            medical excellence, validated on clinical benchmarks.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="text-center p-6 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 neo-shadow hover:neo-shadow-lg transition-all duration-300"
            >
              <div className={`text-3xl font-extrabold ${stat.color} mb-1 font-mono`}>
                {stat.value}
              </div>
              <div className="text-sm font-semibold text-gray-900 dark:text-white mb-0.5">
                {stat.label}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-500">
                {stat.sublabel}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
