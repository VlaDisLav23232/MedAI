import React from "react";
import { Activity, Github } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center">
              <Activity size={14} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              MedAI Clinical Co-Pilot
            </span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-500 text-center">
            Built by BFS Team · Powered by MedGemma & Claude ·{" "}
            <span className="text-accent-rose font-medium">
              Not for clinical use — Research & Demo only
            </span>
          </p>

          <a
            href="https://github.com/ArseniiStratiuk/Agentic-MedAI-SoftServe"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white transition"
          >
            <Github size={16} />
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
