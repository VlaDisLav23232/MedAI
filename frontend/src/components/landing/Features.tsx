"use client";

import React from "react";
import {
  Image,
  FileText,
  AudioLines,
  Clock,
  Layers,
  ShieldCheck,
  Eye,
  Scale,
} from "lucide-react";

const features = [
  {
    icon: Image,
    title: "Medical Image Analysis",
    description:
      "Upload X-rays, CT scans, or pathology slides. MedGemma 4B analyzes with 88.9% macro-F1 on CXR conditions and produces attention heatmaps.",
    color: "from-accent-cyan/20 to-brand-500/20",
    iconColor: "text-accent-cyan",
    tag: "MedGemma 4B + MedSigLIP",
  },
  {
    icon: FileText,
    title: "Clinical Text Reasoning",
    description:
      "Structured chain-of-thought reasoning over patient history, labs, and EHR data. 87.7% accuracy on medical Q&A benchmarks.",
    color: "from-accent-violet/20 to-brand-500/20",
    iconColor: "text-accent-violet",
    tag: "MedGemma 27B",
  },
  {
    icon: AudioLines,
    title: "Audio Analysis",
    description:
      "Process cough patterns, breathing sounds, and lung auscultation. Trained on 313M audio clips via Google's HeAR model.",
    color: "from-accent-amber/20 to-accent-rose/20",
    iconColor: "text-accent-amber",
    tag: "HeAR Encoder",
  },
  {
    icon: Clock,
    title: "Longitudinal Timeline",
    description:
      "A patient's 2023 lab result actively informs today's diagnosis. Semantic search across years of medical history using vector embeddings.",
    color: "from-brand-500/20 to-accent-emerald/20",
    iconColor: "text-brand-500",
    tag: "RAG + Vector DB",
  },
  {
    icon: Scale,
    title: "Multi-Agent Consensus",
    description:
      "Judgment cycles that cross-check image, text, and audio findings for contradictions before any result reaches the doctor.",
    color: "from-accent-emerald/20 to-accent-cyan/20",
    iconColor: "text-accent-emerald",
    tag: "Claude Judge",
  },
  {
    icon: Eye,
    title: "Radical Explainability",
    description:
      "Every AI output is traceable: attention heatmaps, step-by-step reasoning traces, confidence scores, and evidence citations.",
    color: "from-accent-rose/20 to-accent-violet/20",
    iconColor: "text-accent-rose",
    tag: "Core Principle",
  },
  {
    icon: ShieldCheck,
    title: "Doctor-First Workflow",
    description:
      "AI is the assistant, never the authority. Every diagnosis and plan requires explicit doctor approval before becoming record.",
    color: "from-brand-500/20 to-brand-700/20",
    iconColor: "text-brand-600 dark:text-brand-400",
    tag: "Human-in-the-loop",
  },
  {
    icon: Layers,
    title: "Structured Outputs",
    description:
      "All specialist tools return typed JSON with findings, confidence scores, and evidence — fully machine-parseable and auditable.",
    color: "from-accent-cyan/20 to-accent-violet/20",
    iconColor: "text-accent-cyan",
    tag: "JSON Schema",
  },
];

export function Features() {
  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-500 uppercase tracking-wider mb-3">
            Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Multi-Modal Intelligence, Unified
          </h2>
          <p className="max-w-2xl mx-auto text-gray-600 dark:text-gray-400">
            Four specialist AI tools orchestrated by a single intelligent agent.
            Every modality contributes to a complete clinical picture.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group relative rounded-2xl p-6 bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 neo-shadow hover:neo-shadow-lg transition-all duration-300 hover:-translate-y-1"
              >
                {/* Gradient background on hover */}
                <div
                  className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                />

                <div className="relative z-10">
                  {/* Icon */}
                  <div className="w-10 h-10 rounded-xl bg-gray-50 dark:bg-surface-dark-3 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Icon size={20} className={feature.iconColor} />
                  </div>

                  {/* Tag */}
                  <span className="inline-block text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
                    {feature.tag}
                  </span>

                  {/* Title */}
                  <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">
                    {feature.title}
                  </h3>

                  {/* Description */}
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
