"use client";

import React from "react";
import { Lightbulb, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExamplePromptsProps {
  onSelectExample: (prompt: string) => void;
  onDismiss?: () => void;
  className?: string;
}

const E2E_EXAMPLES = [
  {
    title: "Pneumonia / COPD Exacerbation Case",
    description: "62yo male with progressive dyspnea, productive cough, fever",
    prompt: `62-year-old male presents with 3-week progressive dyspnea, productive cough with yellowish sputum, and low-grade fever (37.8°C). 40-pack-year smoking history. Physical exam: decreased breath sounds right lower lobe with dullness to percussion. Please analyze the chest X-ray, reason about the clinical picture, and provide a diagnosis with treatment plan.

Clinical Context:
Vitals: BP 135/85, HR 92, RR 22, SpO2 93% on room air. Weight loss of 4kg over past month.

Patient History:
Past Medical History: COPD (GOLD II), Hypertension, Type 2 Diabetes Mellitus. Previous hospitalizations for pneumonia (2 years ago) and COPD exacerbations (3 times in past 2 years).

Current Medications: Albuterol/Ipratropium inhaler (4 times daily), Lisinopril 10mg daily, Metformin 1000mg twice daily, Atorvastatin 20mg evening.

Allergies: Penicillin (rash).

Social History: Active smoker (40 pack-years), 1-2 alcohol drinks/week, lives alone, retired factory worker.

Lab Results:
- WBC: 14.2 (elevated, normal: 4.0-11.0)
- CRP: 85 (elevated, normal: <10)
- Procalcitonin: 0.8 (elevated, normal: <0.5)
- Hemoglobin: 12.1 (low-normal, normal: 13.5-17.5)
- Creatinine: 1.1 (normal: 0.7-1.3)
- HbA1c: 7.2% (elevated, normal: <5.7%)

Example chest X-ray URL: https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/1-s2.0-S0929664620300449-gr2_lrg-a.jpg`,
  },
  {
    title: "Known COPD Patient Follow-up",
    description: "Maria Ivanova, 58yo female with established COPD history",
    prompt: `Patient Maria Ivanova (PT-DEMO0001) presenting for follow-up evaluation. 58-year-old female with known COPD, currently experiencing increased shortness of breath. Please analyze her clinical timeline, review her history, and provide updated assessment with treatment recommendations.

Please search her patient history for relevant previous encounters and analyze trends in her condition.`,
  },
];

export function ExamplePrompts({ onSelectExample, onDismiss, className }: ExamplePromptsProps) {
  return (
    <div className={cn("p-4 bg-gradient-to-br from-brand-50 to-accent-cyan/5 dark:from-brand-950 dark:to-accent-cyan/5 border border-brand-200 dark:border-brand-800 rounded-xl shadow-sm", className)}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Lightbulb size={18} className="text-brand-500" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Example E2E Test Cases
          </h3>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 rounded hover:bg-brand-100 dark:hover:bg-brand-900 transition"
            aria-label="Dismiss examples"
          >
            <X size={14} className="text-gray-400" />
          </button>
        )}
      </div>

      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
        Click an example to load it into the chat (won't auto-send)
      </p>

      <div className="space-y-2">
        {E2E_EXAMPLES.map((example, i) => (
          <button
            key={i}
            onClick={() => onSelectExample(example.prompt)}
            className="w-full text-left p-3 bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-brand-300 dark:hover:border-brand-700 hover:shadow-md transition group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition">
                  {example.title}
                </h4>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {example.description}
                </p>
              </div>
              <span className="ml-2 text-xs text-brand-500 opacity-0 group-hover:opacity-100 transition">
                Load →
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
