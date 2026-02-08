"use client";

import React, { useState, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";
import { CitationsSidebar } from "@/components/agent/CitationsSidebar";
import { ChatArea } from "@/components/agent/ChatArea";
import { ChatInput } from "@/components/agent/ChatInput";
import { AgentStatusIndicator } from "@/components/shared/AgentStatusIndicator";
import { apiClient } from "@/lib/api/client";
import { mockChatMessages, mockCitations, mockPatient } from "@/lib/mock-data";
import type { ChatMessage, AgentStatus, Citation } from "@/lib/types";
import {
  PanelLeftOpen,
  PanelLeftClose,
  User,
  Activity,
  Settings,
  Wifi,
  WifiOff,
} from "lucide-react";

export default function AgentPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Check backend availability on mount
  useEffect(() => {
    apiClient.isBackendAvailable().then(setBackendOnline);
  }, []);

  const handleSend = useCallback(
    async (text: string, _attachments?: File[]) => {
      // Add user message
      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setAgentStatus("routing");

      // Attempt real API call
      if (backendOnline) {
        try {
          setAgentStatus("analyzing_text");
          const res = await apiClient.analyzeCase({
            patient_id: mockPatient.id,
            doctor_query: text,
          });
          setAgentStatus("complete");

          const agentMsg: ChatMessage = {
            id: `msg-${Date.now() + 1}`,
            role: "agent",
            content: `**Diagnosis:** ${res.diagnosis} (${Math.round(res.confidence * 100)}% confidence)\n\n${res.evidence_summary}\n\n**Plan:**\n${res.plan.map((p) => `- ${p}`).join("\n")}`,
            timestamp: new Date().toISOString(),
            citations: res.findings.map((f, i) => ({
              id: `cit-${i}`,
              type: "finding" as const,
              title: f.finding,
              content: f.explanation,
              source: "AI Analysis",
              confidence: f.confidence,
            })),
          };

          setCitations(agentMsg.citations ?? []);
          setMessages((prev) => [...prev, agentMsg]);
          setTimeout(() => setAgentStatus("idle"), 2000);
          return;
        } catch {
          // Fall through to mock on error
        }
      }

      // Mock fallback simulation
      setTimeout(() => setAgentStatus("analyzing_image"), 800);
      setTimeout(() => setAgentStatus("searching_history"), 2000);
      setTimeout(() => setAgentStatus("analyzing_text"), 3500);
      setTimeout(() => setAgentStatus("judging"), 5000);
      setTimeout(() => setAgentStatus("generating_report"), 6000);
      setTimeout(() => {
        setCitations(mockCitations);
        setMessages((prev) => [...prev, mockChatMessages[1], mockChatMessages[2]]);
        setAgentStatus("complete");
      }, 7000);
      setTimeout(() => setAgentStatus("idle"), 9000);
    },
    [backendOnline]
  );

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

            {backendOnline !== null && (
              <div
                className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium",
                  backendOnline
                    ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400"
                )}
                title={backendOnline ? "Connected to backend" : "Using mock data"}
              >
                {backendOnline ? <Wifi size={10} /> : <WifiOff size={10} />}
                {backendOnline ? "Live" : "Mock"}
              </div>
            )}

            <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

            <button
              onClick={handleLoadDemo}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/30 transition"
            >
              <Activity size={12} />
              Load Demo
            </button>

            <button className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition text-gray-400" aria-label="Settings (coming soon)" title="Settings — coming soon" disabled>
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
          onPromptClick={(prompt) => handleSend(prompt)}
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
