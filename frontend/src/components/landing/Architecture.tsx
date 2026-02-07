"use client";

import React from "react";

const steps = [
  {
    num: "01",
    title: "Doctor Query",
    description: "Doctor uploads data (image, text, audio) with clinical context and a specific question.",
    color: "border-brand-500",
    bg: "bg-brand-500/10",
    textColor: "text-brand-500",
  },
  {
    num: "02",
    title: "Orchestrator Routes",
    description: "Claude analyzes the query, plans subtasks, and dispatches to relevant specialist tools in parallel.",
    color: "border-accent-violet",
    bg: "bg-accent-violet/10",
    textColor: "text-accent-violet",
  },
  {
    num: "03",
    title: "Specialist Analysis",
    description: "MedGemma (image/text), HeAR (audio), and RAG (history) tools produce structured JSON findings.",
    color: "border-accent-cyan",
    bg: "bg-accent-cyan/10",
    textColor: "text-accent-cyan",
  },
  {
    num: "04",
    title: "Judgment Cycle",
    description: "Judge Agent checks for contradictions, low confidence, and guideline compliance — re-queries if needed.",
    color: "border-accent-emerald",
    bg: "bg-accent-emerald/10",
    textColor: "text-accent-emerald",
  },
  {
    num: "05",
    title: "Explainable Report",
    description: "Structured report with diagnosis, evidence trails, heatmaps, reasoning traces, and confidence scores.",
    color: "border-accent-amber",
    bg: "bg-accent-amber/10",
    textColor: "text-accent-amber",
  },
  {
    num: "06",
    title: "Doctor Decides",
    description: "Doctor reviews, edits, approves or rejects. AI never acts autonomously — human always in the loop.",
    color: "border-accent-rose",
    bg: "bg-accent-rose/10",
    textColor: "text-accent-rose",
  },
];

export function Architecture() {
  return (
    <section className="py-24 relative bg-gray-50/50 dark:bg-surface-dark-2/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-500 uppercase tracking-wider mb-3">
            How It Works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            From Query to Decision in 6 Steps
          </h2>
          <p className="max-w-2xl mx-auto text-gray-600 dark:text-gray-400">
            A transparent, traceable pipeline — every step is visible, every
            decision is explainable.
          </p>
        </div>

        {/* Pipeline steps */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <div
              key={step.num}
              className={`relative rounded-2xl p-6 bg-white dark:bg-surface-dark border-l-4 ${step.color} neo-shadow`}
            >
              {/* Step number */}
              <div
                className={`inline-flex items-center justify-center w-10 h-10 rounded-xl ${step.bg} mb-4`}
              >
                <span className={`text-sm font-bold font-mono ${step.textColor}`}>
                  {step.num}
                </span>
              </div>

              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {step.description}
              </p>

              {/* Connector arrow (hidden on last and odd positions on large screens etc.) */}
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 text-gray-300 dark:text-gray-700">
                  {(i + 1) % 3 !== 0 && (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M5 12H19M19 12L12 5M19 12L12 19"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Architecture diagram label */}
        <div className="mt-16 text-center">
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-2xl glass-card neo-shadow">
            <div className="flex -space-x-1.5">
              <div className="w-3 h-3 rounded-full bg-brand-500 ring-2 ring-white dark:ring-surface-dark" />
              <div className="w-3 h-3 rounded-full bg-accent-cyan ring-2 ring-white dark:ring-surface-dark" />
              <div className="w-3 h-3 rounded-full bg-accent-violet ring-2 ring-white dark:ring-surface-dark" />
              <div className="w-3 h-3 rounded-full bg-accent-emerald ring-2 ring-white dark:ring-surface-dark" />
            </div>
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Routing → Parallelization → Voting → Evaluator-Optimizer → Human-in-the-loop
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
