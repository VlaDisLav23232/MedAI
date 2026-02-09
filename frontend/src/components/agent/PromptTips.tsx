"use client";

import React, { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  Info,
  X,
  Lightbulb,
  Stethoscope,
  Image as ImageIcon,
  AudioLines,
  History,
  ChevronRight,
} from "lucide-react";

interface PromptTipsProps {
  className?: string;
}

const tips = [
  {
    icon: Stethoscope,
    title: "Be specific about symptoms",
    description:
      "Include duration, severity, location, and onset. E.g. \"Sharp right-lower chest pain for 3 days, worsens on inspiration\"",
    color: "text-brand-500",
    bgColor: "bg-brand-50 dark:bg-brand-900/20",
  },
  {
    icon: ImageIcon,
    title: "Describe imaging context",
    description:
      "When uploading X-rays or scans, mention the modality, view, and clinical question. E.g. \"PA chest X-ray for suspected pneumonia\"",
    color: "text-accent-cyan",
    bgColor: "bg-cyan-50 dark:bg-cyan-900/20",
  },
  {
    icon: History,
    title: "Include relevant history",
    description:
      "Mention chronic conditions, medications, allergies, and prior procedures. The AI cross-references with patient timeline data.",
    color: "text-accent-violet",
    bgColor: "bg-violet-50 dark:bg-violet-900/20",
  },
  {
    icon: AudioLines,
    title: "Audio recordings",
    description:
      "Attach lung sounds, heart auscultation, or cough recordings. Specify location (e.g. \"right lower lobe\") and patient position.",
    color: "text-accent-amber",
    bgColor: "bg-amber-50 dark:bg-amber-900/20",
  },
  {
    icon: Lightbulb,
    title: "Ask focused questions",
    description:
      "\"What's the differential for...\" or \"Compare with previous scan from January\" yields better results than vague queries.",
    color: "text-accent-emerald",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
  },
];

const examplePrompts = [
  "56yo male, diabetic, presents with sudden onset chest pain radiating to left arm. BP 160/95, HR 110. ECG shows ST elevation in leads II, III, aVF. Suggest differential and urgent workup.",
  "Follow-up for Patient with known COPD. Current complaint: worsening dyspnea over 2 weeks, productive cough with yellow sputum. Compare with previous spirometry results.",
  "Analyze attached chest X-ray. Clinical context: 72yo female, post-op day 3 after hip replacement, sudden onset tachypnea and pleuritic chest pain. Rule out PE/pneumonia.",
];

export function PromptTips({ className }: PromptTipsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    function handleClick(e: MouseEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen]);

  return (
    <div className={cn("relative inline-flex", className)}>
      {/* Trigger button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-all duration-200",
          isOpen
            ? "bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400"
            : "text-gray-400 hover:text-brand-500 hover:bg-gray-100 dark:hover:bg-surface-dark-3"
        )}
        aria-label="Prompt writing tips"
        aria-expanded={isOpen}
        title="Tips for writing better prompts"
      >
        <Info size={14} />
        <span className="hidden sm:inline">Tips</span>
      </button>

      {/* Floating panel */}
      {isOpen && (
        <div
          ref={panelRef}
          className={cn(
            "absolute bottom-full right-0 mb-2 w-[380px] max-h-[70vh] overflow-y-auto",
            "bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700",
            "rounded-2xl shadow-xl dark:shadow-2xl",
            "animate-slide-up z-50"
          )}
          role="dialog"
          aria-label="Prompt tips"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 sticky top-0 bg-white dark:bg-surface-dark-2 rounded-t-2xl">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center">
                <Lightbulb size={14} className="text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                  Writing Better Prompts
                </h3>
                <p className="text-[10px] text-gray-400">
                  Get more accurate AI analysis
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition"
              aria-label="Close tips"
            >
              <X size={14} className="text-gray-400" />
            </button>
          </div>

          {/* Tips list */}
          <div className="px-4 py-3 space-y-2.5">
            {tips.map((tip, i) => {
              const Icon = tip.icon;
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                      tip.bgColor
                    )}
                  >
                    <Icon size={14} className={tip.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-semibold text-gray-900 dark:text-white">
                      {tip.title}
                    </h4>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
                      {tip.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Example prompts toggle */}
          <div className="border-t border-gray-100 dark:border-gray-800">
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="flex items-center justify-between w-full px-4 py-2.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/10 transition"
            >
              <span>Example prompts</span>
              <ChevronRight
                size={14}
                className={cn(
                  "transition-transform",
                  showExamples && "rotate-90"
                )}
              />
            </button>

            {showExamples && (
              <div className="px-4 pb-3 space-y-2">
                {examplePrompts.map((prompt, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-gray-50 dark:bg-surface-dark-3 border border-gray-100 dark:border-gray-700"
                  >
                    <p className="text-[11px] text-gray-600 dark:text-gray-400 leading-relaxed italic">
                      &ldquo;{prompt}&rdquo;
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-surface-dark-3/50 rounded-b-2xl">
            <p className="text-[10px] text-gray-400 text-center">
              More context = better analysis. Include vitals, meds, and history when possible.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
