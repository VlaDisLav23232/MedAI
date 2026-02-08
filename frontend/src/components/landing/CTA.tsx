"use client";

import React from "react";
import Link from "next/link";
import { Bot, ArrowRight, Shield } from "lucide-react";

export function CTA() {
  return (
    <section className="py-24 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-brand-950 via-brand-900 to-surface-dark" />
      <div className="absolute inset-0 grid-bg opacity-30" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 border border-white/10 text-white/80 text-xs font-semibold uppercase tracking-wider mb-6">
          <Shield size={12} />
          Research & Demonstration Only
        </div>

        <h2 className="text-3xl sm:text-5xl font-extrabold text-white mb-6 leading-tight">
          Ready to Experience
          <br />
          <span className="gradient-text">Agentic Medical AI?</span>
        </h2>

        <p className="text-lg text-gray-300 mb-10 max-w-xl mx-auto">
          Upload a medical image, provide patient context, and watch the
          multi-agent system analyze, reason, cross-reference, and explain
          — in real time.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/agent"
            className="inline-flex items-center gap-2 px-8 py-4 bg-white text-brand-900 font-bold rounded-2xl hover:bg-gray-100 transition-all duration-200 shadow-xl shadow-black/20 active:scale-[0.98]"
          >
            <Bot size={20} />
            Launch Clinical Co-Pilot
            <ArrowRight size={16} />
          </Link>
          <Link
            href="/patients"
            className="inline-flex items-center gap-2 px-8 py-4 bg-white/10 text-white font-semibold rounded-2xl border border-white/20 hover:bg-white/20 transition-all duration-200 active:scale-[0.98]"
          >
            Browse Patients
          </Link>
        </div>

        <p className="mt-8 text-xs text-gray-500">
          Not for clinical use. Always consult a qualified healthcare professional for medical decisions.
        </p>
      </div>
    </section>
  );
}
