"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { CitationsSidebar } from "@/components/agent/CitationsSidebar";
import { ChatArea } from "@/components/agent/ChatArea";
import { ChatInput } from "@/components/agent/ChatInput";

import { PromptTips } from "@/components/agent/PromptTips";
import { ExamplePrompts } from "@/components/agent/ExamplePrompts";

import { AgentStatusIndicator } from "@/components/shared/AgentStatusIndicator";
import { PatientSelector } from "@/components/agent/PatientSelector";
import { useToast } from "@/components/shared/Toast";
import { apiClient } from "@/lib/api/client";
import { mapApiResponseToAIReport } from "@/lib/api/mappers";
import { useChatStore, useUIStore } from "@/lib/store";
import { getFileCategory } from "@/lib/file-upload";
import type { ChatMessage } from "@/lib/types";
import {
  PanelLeftOpen,
  PanelLeftClose,
  Activity,
  Settings,
  Wifi,
  WifiOff,
} from "lucide-react";

export default function AgentPage() {
  const searchParams = useSearchParams();

  // Local state for controlled chat input
  const [inputValue, setInputValue] = useState("");
  const [showExamples, setShowExamples] = useState(true);

  // Zustand chat store
  const messages = useChatStore((s) => s.messages);
  const addMessage = useChatStore((s) => s.addMessage);
  const setMessages = useChatStore((s) => s.setMessages);
  const citations = useChatStore((s) => s.citations);
  const setCitations = useChatStore((s) => s.setCitations);
  const agentStatus = useChatStore((s) => s.agentStatus);
  const setAgentStatus = useChatStore((s) => s.setAgentStatus);
  const sidebarOpen = useChatStore((s) => s.sidebarOpen);
  const setSidebarOpen = useChatStore((s) => s.setSidebarOpen);
  const currentPatient = useChatStore((s) => s.currentPatient);

  // UI store — backend health
  const backendOnline = useUIStore((s) => s.backendOnline);
  const setBackendOnline = useUIStore((s) => s.setBackendOnline);

  // Toast notifications
  const { error: toastError, success: toastSuccess, warning: toastWarning } = useToast();

  // Check backend availability on mount
  useEffect(() => {
    apiClient.isBackendAvailable().then(setBackendOnline);
  }, [setBackendOnline]);

  // Pre-select patient from URL param ?patientId=
  const urlPatientId = searchParams.get("patientId");

  const handleSend = useCallback(
    async (text: string, attachments?: File[]) => {
      if (!currentPatient) return;

      // Add user message with attachment info
      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
        attachments: attachments?.map((f, i) => ({
          id: `att-${Date.now()}-${i}`,
          type: getFileCategory(f),
          name: f.name,
          url: URL.createObjectURL(f),
        })),
      };
      addMessage(userMsg);
      setAgentStatus("routing");

      if (!backendOnline) {
        setAgentStatus("error");
        toastError("Backend Unavailable", "Please check that the server is running on port 8000.");
        const errMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          role: "system",
          content: "Backend is unavailable. Please check that the server is running on port 8000.",
          timestamp: new Date().toISOString(),
        };
        addMessage(errMsg);
        return;
      }

      try {
        setAgentStatus("analyzing_text");

        // Upload attached files to server first, get back URLs sorted by category
        let imageUrls: string[] = [];
        let audioUrls: string[] = [];
        let documentUrls: string[] = [];

        if (attachments && attachments.length > 0) {
          const uploadRes = await apiClient.uploadFiles(attachments);
          if (uploadRes.error) {
            throw new Error(`File upload failed: ${uploadRes.error}`);
          }
          imageUrls = uploadRes.data?.image_urls ?? [];
          audioUrls = uploadRes.data?.audio_urls ?? [];
          documentUrls = uploadRes.data?.document_urls ?? [];
        }

        const res = await apiClient.analyzeCase({
          patient_id: currentPatient.id,
          doctor_query: text,
          ...(imageUrls.length > 0 && { image_urls: imageUrls }),
          ...(audioUrls.length > 0 && { audio_urls: audioUrls }),
          ...(documentUrls.length > 0 && { document_urls: documentUrls }),
        });

        if (res.error || !res.data) {
          throw new Error(res.error || "Analysis returned no data");
        }
        const data = res.data;
        setAgentStatus("complete");

        // Map the response to a structured AI report
        const mappedReport = mapApiResponseToAIReport(data);

        // Build rich citations from findings + specialist summaries
        const allCitations: import("@/lib/types").Citation[] = [];

        // Findings → "finding" type citations
        data.findings.forEach((f, i) => {
          allCitations.push({
            id: `cit-finding-${i}`,
            type: "finding",
            title: f.finding,
            content: f.explanation,
            source: "AI Analysis",
            confidence: f.confidence,
          });
        });

        // Specialist summaries → typed citations for sidebar tabs
        if (data.specialist_summaries) {
          Object.entries(data.specialist_summaries).forEach(([tool, summary], i) => {
            if (tool.includes("image") || tool === "image_analysis") {
              allCitations.push({
                id: `cit-imaging-${i}`,
                type: "imaging",
                title: "Image Analysis",
                content: summary,
                source: tool,
              });
            } else if (tool.includes("history") || tool === "history_search") {
              allCitations.push({
                id: `cit-history-${i}`,
                type: "history",
                title: "Patient History",
                content: summary,
                source: tool,
              });
            } else if (tool.includes("audio") || tool === "audio_analysis") {
              allCitations.push({
                id: `cit-lab-${i}`,
                type: "lab",
                title: "Audio Analysis",
                content: summary,
                source: tool,
              });
            } else if (tool.includes("text") || tool.includes("reasoning") || tool === "text_reasoning") {
              allCitations.push({
                id: `cit-guideline-${i}`,
                type: "guideline",
                title: "Clinical Reasoning",
                content: summary,
                source: tool,
              });
            }
          });
        }

        const agentMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          role: "agent",
          content: `**Diagnosis:** ${data.diagnosis} (${Math.round(data.confidence * 100)}% confidence)\n\n${data.evidence_summary}\n\n**Plan:**\n${data.plan.map((p) => `- ${p}`).join("\n")}\n\n[View Full Report →](/case/${data.report_id})`,
          timestamp: new Date().toISOString(),
          report: mappedReport,
          citations: allCitations,
        };

        setCitations(agentMsg.citations ?? []);
        addMessage(agentMsg);
        toastSuccess("Analysis Complete", `Report ${res.report_id} generated with ${Math.round(res.confidence * 100)}% confidence.`);
        setTimeout(() => setAgentStatus("idle"), 2000);
      } catch (err) {
        setAgentStatus("error");
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        toastError("Analysis Failed", errorMessage);
        const errMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          role: "system",
          content: `Analysis failed: ${errorMessage}. Please try again.`,
          timestamp: new Date().toISOString(),
        };
        addMessage(errMsg);
      }
    },
    [backendOnline, currentPatient, addMessage, setAgentStatus, setCitations, toastError, toastSuccess]
  );

  const handleReset = useCallback(() => {
    setMessages([]);
    setCitations([]);
    setAgentStatus("idle");
    setInputValue("");
    setShowExamples(true);
  }, [setMessages, setCitations, setAgentStatus]);

  const handleSelectExample = useCallback((prompt: string) => {
    setInputValue(prompt);
    setShowExamples(false);
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

            {/* Patient selector */}
            <PatientSelector preselectedId={urlPatientId ?? undefined} />
          </div>

          <div className="flex items-center gap-3">
            <AgentStatusIndicator status={agentStatus} />

            <div
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium",
                backendOnline
                  ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400"
                  : "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400"
              )}
              title={backendOnline ? "Connected to backend" : "Backend offline"}
            >
              {backendOnline ? <Wifi size={10} /> : <WifiOff size={10} />}
              {backendOnline ? "Live" : "Offline"}
            </div>

            <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/30 transition"
            >
              <Activity size={12} />
              New Chat
            </button>

            <button className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition text-gray-400" aria-label="Settings (coming soon)" title="Settings — coming soon" disabled>
              <Settings size={16} />
            </button>
          </div>
        </div>

        {/* Chat messages */}
        <ChatArea
          messages={messages}
          onCitationClick={() => {
            setSidebarOpen(true);
          }}
          onPromptClick={(prompt) => handleSend(prompt)}
          className="flex-1"
        />

        {/* Chat input */}
        <div className="p-4 bg-white dark:bg-surface-dark-2 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2 mb-1 justify-end">
            <PromptTips />
          </div>
          {/* Show example prompts when no messages yet */}
          {messages.length === 0 && showExamples && currentPatient && (
            <ExamplePrompts
              onSelectExample={handleSelectExample}
              onDismiss={() => setShowExamples(false)}
              className="mb-4"
            />
          )}

          <ChatInput
            onSend={handleSend}
            value={inputValue}
            onValueChange={setInputValue}
            disabled={
              (agentStatus !== "idle" && agentStatus !== "complete" && agentStatus !== "error") ||
              !currentPatient
            }
          />
          {!currentPatient && (
            <p className="text-xs text-amber-500 text-center mt-2">
              Select a patient above to start the analysis.
            </p>
          )}
          <p className="text-[10px] text-gray-400 text-center mt-2">
            AI-assisted analysis — always verify with clinical judgment. Not for direct patient use.
          </p>
        </div>
      </div>
    </div>
  );
}
