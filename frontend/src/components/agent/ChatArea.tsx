"use client";

import React, { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { ChatMessage } from "./ChatMessage";
import { Bot, Sparkles } from "lucide-react";

interface ChatAreaProps {
  messages: ChatMessageType[];
  onCitationClick?: (citationId: string) => void;
  onPromptClick?: (prompt: string) => void;
  className?: string;
}

export function ChatArea({ messages, onCitationClick, onPromptClick, className }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className={cn("flex-1 overflow-y-auto", className)}>
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center px-6">
          {/* Empty state */}
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center mb-6 animate-float">
            <Bot size={28} className="text-white" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Clinical Co-Pilot Ready
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-8">
            Upload a medical image, share patient history, or describe a clinical case.
            The AI agent will analyze, reason, cross-reference, and produce an explainable report.
          </p>

          {/* Suggested prompts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
            {[
              "Analyze this chest X-ray for any pathology",
              "Review patient labs and imaging history",
              "Differential diagnosis for persistent cough with fever",
              "Compare current scan with previous baseline",
            ].map((prompt) => (
              <button
                key={prompt}
                onClick={() => onPromptClick?.(prompt)}
                className="flex items-start gap-2 px-4 py-3 rounded-xl text-left text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 hover:border-brand-300 dark:hover:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/10 transition-all duration-200 group"
              >
                <Sparkles size={14} className="text-brand-400 mt-0.5 flex-shrink-0 group-hover:text-brand-500" />
                <span>{prompt}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onCitationClick={onCitationClick}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
