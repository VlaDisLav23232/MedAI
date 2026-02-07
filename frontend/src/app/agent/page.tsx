"use client";

import React, { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { CitationsSidebar } from "@/components/agent/CitationsSidebar";
import { ChatArea } from "@/components/agent/ChatArea";
import { ChatInput } from "@/components/agent/ChatInput";
import { AgentStatusIndicator } from "@/components/shared/AgentStatusIndicator";
import { mockChatMessages, mockCitations, mockPatient } from "@/lib/mock-data";
import type { ChatMessage, AgentStatus, Citation } from "@/lib/types";
import {
  PanelLeftOpen,
  PanelLeftClose,
  User,
  Activity,
  Settings,
} from "lucide-react";

export default function AgentPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const [citations, setCitations] = useState<Citation[]>([]);

  const handleSend = useCallback((text: string) => {
    // Add user message
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setAgentStatus("routing");

    // Simulate agent processing pipeline
    setTimeout(() => {
      setAgentStatus("analyzing_image");
    }, 800);

    setTimeout(() => {
      setAgentStatus("searching_history");
    }, 2000);

    setTimeout(() => {
      setAgentStatus("analyzing_text");
    }, 3500);

    setTimeout(() => {
      setAgentStatus("judging");
    }, 5000);

    setTimeout(() => {
      setAgentStatus("generating_report");
    }, 6000);

    // Add mock agent responses after delay
    setTimeout(() => {
      setCitations(mockCitations);
      setMessages((prev) => [...prev, mockChatMessages[1], mockChatMessages[2]]);
      setAgentStatus("complete");
    }, 7000);

    setTimeout(() => {
      setAgentStatus("idle");
    }, 9000);
  }, []);

  const handleLoadDemo = useCallback(() => {
    setMessages(mockChatMessages);
    setCitations(mockCitations);
    setAgentStatus("complete");
    setTimeout(() => setAgentStatus("idle"), 2000);
  }, []);

  return (
    <div className="flex h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* Left sidebar — Citations & Evidence */}
      <CitationsSidebar
        citations={citations}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark-2">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition text-gray-400"
                title="Open evidence panel"
              >
                <PanelLeftOpen size={18} />
              </button>
            )}
            {sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition text-gray-400"
                title="Close evidence panel"
              >
                <PanelLeftClose size={18} />
              </button>
            )}

            <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

            {/* Patient context */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <User size={14} className="text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <span className="text-xs font-semibold text-gray-900 dark:text-white block leading-none">
                  {mockPatient.name}
                </span>
                <span className="text-[10px] text-gray-400">
                  {mockPatient.medical_record_number}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <AgentStatusIndicator status={agentStatus} />

            <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

            <button
              onClick={handleLoadDemo}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/30 transition"
            >
              <Activity size={12} />
              Load Demo
            </button>

            <button className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition text-gray-400">
              <Settings size={16} />
            </button>
          </div>
        </div>

        {/* Chat messages */}
        <ChatArea
          messages={messages}
          onCitationClick={(id) => {
            setSidebarOpen(true);
          }}
          className="flex-1"
        />

        {/* Chat input */}
        <div className="p-4 bg-white dark:bg-surface-dark-2 border-t border-gray-200 dark:border-gray-800">
          <ChatInput
            onSend={handleSend}
            disabled={agentStatus !== "idle" && agentStatus !== "complete"}
          />
          <p className="text-[10px] text-gray-400 text-center mt-2">
            AI-assisted analysis — always verify with clinical judgment. Not for direct patient use.
          </p>
        </div>
      </div>
    </div>
  );
}
