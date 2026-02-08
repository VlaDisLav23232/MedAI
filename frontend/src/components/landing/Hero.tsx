"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, Bot, Sparkles } from "lucide-react";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background layers */}
      <div className="absolute inset-0 bg-gradient-to-br from-white via-brand-50/40 to-white dark:from-surface-dark dark:via-brand-950/30 dark:to-surface-dark" />
      <div className="absolute inset-0 grid-bg" />

      {/* Animated gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-brand-400/10 dark:bg-brand-500/10 rounded-full blur-3xl animate-float" />
      <div
        className="absolute bottom-1/4 -right-32 w-80 h-80 bg-accent-cyan/10 dark:bg-accent-cyan/10 rounded-full blur-3xl animate-float"
        style={{ animationDelay: "2s" }}
      />
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent-violet/5 dark:bg-accent-violet/5 rounded-full blur-3xl"
      />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card neo-shadow mb-8 animate-fade-in">
          <Sparkles size={14} className="text-brand-500" />
          <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
            Agentic Intelligence for Healthcare
          </span>
        </div>

        {/* Main heading */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 animate-slide-up">
          <span className="text-gray-900 dark:text-white">Clinical </span>
          <span className="gradient-text">Co-Pilot</span>
          <br />
          <span className="text-gray-900 dark:text-white">for Modern </span>
          <span className="gradient-text">Medicine</span>
        </h1>

        {/* Sub-heading */}
        <p className="max-w-2xl mx-auto text-lg sm:text-xl text-gray-600 dark:text-gray-400 leading-relaxed mb-10 animate-slide-up" style={{ animationDelay: "0.1s" }}>
          Eliminate medical dark data. Multi-modal AI that{" "}
          <span className="font-semibold text-gray-900 dark:text-gray-200">
            analyzes images, reasons over text, processes audio
          </span>
          , and cross-references a patient&apos;s entire history — with radical
          explainability at every step.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <Link href="/agent" className="btn-primary flex items-center gap-2 text-base px-8 py-3.5">
            <Bot size={18} />
            Launch Co-Pilot
            <ArrowRight size={16} />
          </Link>
          <Link href="/patients" className="btn-secondary flex items-center gap-2 text-base px-8 py-3.5">
            View Patients
          </Link>
        </div>

        {/* Trust bar */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-6 text-xs text-gray-400 dark:text-gray-500 animate-fade-in" style={{ animationDelay: "0.4s" }}>
          <span className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-emerald" />
            Powered by MedGemma
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-500" />
            Orchestrated by Claude
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-violet" />
            Open-Source Models
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-amber" />
            Doctor-First Design
          </span>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white dark:from-surface-dark to-transparent" />
    </section>
  );
}
