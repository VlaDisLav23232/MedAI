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
import type { PipelineEvent } from "@/lib/api/client";
import { mapApiResponseToAIReport } from "@/lib/api/mappers";
import { useChatStore, useUIStore } from "@/lib/store";
import { getFileCategory } from "@/lib/file-upload";
import type { ChatMessage, ToolResult } from "@/lib/types";
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

      // Live pipeline progress message — updated in real-time via SSE events
      const progressMsgId = `msg-progress-${Date.now()}`;
      const toolResults: ToolResult[] = [];
      let currentPhaseMsg = "Routing case to specialist tools…";

      const updateProgressMessage = () => {
        const progressMsg: ChatMessage = {
          id: progressMsgId,
          role: "agent",
          content: `**Pipeline:** ${currentPhaseMsg}`,
          timestamp: new Date().toISOString(),
          toolResults: [...toolResults],
        };
        // Replace the progress message in-place
        setMessages((prev: ChatMessage[]) => {
          const idx = prev.findIndex((m: ChatMessage) => m.id === progressMsgId);
          if (idx === -1) return [...prev, progressMsg];
          const next = [...prev];
          next[idx] = progressMsg;
          return next;
        });
      };

      // Show initial progress
      updateProgressMessage();

      try {
        // Upload attached files to server first
        let imageUrls: string[] = [];
        let audioUrls: string[] = [];
        let documentUrls: string[] = [];

        if (attachments && attachments.length > 0) {
          currentPhaseMsg = "Uploading files…";
          updateProgressMessage();

          const uploadRes = await apiClient.uploadFiles(attachments);
          if (uploadRes.error) {
            throw new Error(`File upload failed: ${uploadRes.error}`);
          }
          imageUrls = uploadRes.data?.image_urls ?? [];
          audioUrls = uploadRes.data?.audio_urls ?? [];
          documentUrls = uploadRes.data?.document_urls ?? [];
        }

        setAgentStatus("analyzing_text");

        const analysisRequest = {
          patient_id: currentPatient.id,
          doctor_query: text,
          ...(imageUrls.length > 0 && { image_urls: imageUrls }),
          ...(audioUrls.length > 0 && { audio_urls: audioUrls }),
          ...(documentUrls.length > 0 && { document_urls: documentUrls }),
        };

        // Map SSE event types to human-friendly AgentStatus values
        const phaseToStatus: Record<string, string> = {
          routing: "routing",
          tools: "analyzing_text",
          judging: "judging",
          generating_report: "generating_report",
        };

        const toolDisplayNames: Record<string, string> = {
          image_analysis: "Image Analysis (MedGemma 4B)",
          text_reasoning: "Text Reasoning (MedGemma 27B)",
          audio_analysis: "Audio Analysis (HeAR)",
          history_search: "History Search",
          image_explainability: "Explainability Heatmaps (MedSigLIP)",
        };

        // Handle pipeline events from SSE
        const handlePipelineEvent = (event: PipelineEvent) => {
          console.log("[Pipeline]", event.type, event);

          switch (event.type) {
            case "pipeline_start":
              currentPhaseMsg = "Pipeline started — routing to specialists…";
              updateProgressMessage();
              break;

            case "phase_start":
              if (event.phase && phaseToStatus[event.phase]) {
                setAgentStatus(phaseToStatus[event.phase] as any);
              }
              currentPhaseMsg = event.message || `Phase: ${event.phase}`;
              updateProgressMessage();
              break;

            case "tool_start": {
              const displayName = toolDisplayNames[event.tool || ""] || event.tool || "Unknown";
              // Add or update this tool in running state
              const existingIdx = toolResults.findIndex((t) => t.tool === displayName);
              if (existingIdx === -1) {
                toolResults.push({ tool: displayName, status: "running" });
              } else {
                toolResults[existingIdx] = { tool: displayName, status: "running" };
              }
              // Update status based on tool type
              if (event.tool?.includes("image")) setAgentStatus("analyzing_image");
              else if (event.tool?.includes("audio")) setAgentStatus("analyzing_audio");
              else if (event.tool?.includes("history")) setAgentStatus("searching_history");
              else setAgentStatus("analyzing_text");
              updateProgressMessage();
              break;
            }

            case "tool_complete": {
              const displayName = toolDisplayNames[event.tool || ""] || event.tool || "Unknown";
              const idx = toolResults.findIndex((t) => t.tool === displayName);
              const durationMs = event.elapsed_s ? Math.round(event.elapsed_s * 1000) : undefined;
              if (idx !== -1) {
                toolResults[idx] = { tool: displayName, status: "complete", duration_ms: durationMs };
              } else {
                toolResults.push({ tool: displayName, status: "complete", duration_ms: durationMs });
              }
              updateProgressMessage();
              break;
            }

            case "tool_error": {
              const displayName = toolDisplayNames[event.tool || ""] || event.tool || "Unknown";
              const idx = toolResults.findIndex((t) => t.tool === displayName);
              const durationMs = event.elapsed_s ? Math.round(event.elapsed_s * 1000) : undefined;
              if (idx !== -1) {
                toolResults[idx] = { tool: displayName, status: "error", duration_ms: durationMs, summary: event.error };
              } else {
                toolResults.push({ tool: displayName, status: "error", duration_ms: durationMs, summary: event.error });
              }
              updateProgressMessage();
              break;
            }

            case "phase_complete":
              currentPhaseMsg = `${event.phase} complete (${event.elapsed_s?.toFixed(1)}s)`;
              updateProgressMessage();
              break;
          }
        };

        // Try SSE streaming first, fall back to synchronous
        let res = await apiClient.analyzeCaseStream(analysisRequest, handlePipelineEvent);
        if (res.error && res.error.includes("Stream failed")) {
          // Fallback to synchronous endpoint
          console.warn("[Pipeline] SSE failed, falling back to sync");
          res = await apiClient.analyzeCase(analysisRequest);
        }

        if (res.error || !res.data) {
          throw new Error(res.error || "Analysis returned no data");
        }
        const data = res.data;
        setAgentStatus("complete");

        // Remove the progress message — replace with final agent response
        setMessages((prev: ChatMessage[]) => prev.filter((m: ChatMessage) => m.id !== progressMsgId));

        // Map the response to a structured AI report
        const mappedReport = mapApiResponseToAIReport(data);

        // Build rich citations from findings + specialist summaries
        const allCitations: import("@/lib/types").Citation[] = [];

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

        // Build pipeline timing summary from metrics
        let metricsLine = "";
        if (data.pipeline_metrics) {
          const m = data.pipeline_metrics;
          const toolLines = Object.entries(m.tool_timings)
            .map(([t, s]) => `${toolDisplayNames[t] || t}: ${s.toFixed(1)}s`)
            .join(", ");
          metricsLine = `\n\n**Pipeline:** ${m.total_s.toFixed(1)}s total (tools: ${m.tools_s.toFixed(1)}s, judge: ${m.judge_s.toFixed(1)}s, report: ${m.report_s.toFixed(1)}s)${toolLines ? `\n**Tools:** ${toolLines}` : ""}`;
        }

        // Build final tool results from pipeline_metrics for the message
        const finalToolResults: ToolResult[] = [];
        if (data.pipeline_metrics) {
          for (const [tool, elapsed] of Object.entries(data.pipeline_metrics.tool_timings)) {
            const displayName = toolDisplayNames[tool] || tool;
            const isFailed = data.pipeline_metrics.tools_failed.includes(tool);
            finalToolResults.push({
              tool: displayName,
              status: isFailed ? "error" : "complete",
              duration_ms: Math.round(elapsed * 1000),
            });
          }
        }

        const agentMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          role: "agent",
          content: `**Diagnosis:** ${data.diagnosis} (${Math.round(data.confidence * 100)}% confidence)\n\n${data.evidence_summary}\n\n**Plan:**\n${data.plan.map((p) => `- ${p}`).join("\n")}${metricsLine}\n\n[View Full Report →](/case/${data.report_id})`,
          timestamp: new Date().toISOString(),
          report: mappedReport,
          citations: allCitations,
          toolResults: finalToolResults,
        };

        setCitations(agentMsg.citations ?? []);
        addMessage(agentMsg);
        toastSuccess("Analysis Complete", `Report ${data.report_id} generated with ${Math.round(data.confidence * 100)}% confidence.`);
        setTimeout(() => setAgentStatus("idle"), 2000);
      } catch (err) {
        // Remove progress message on error
        setMessages((prev: ChatMessage[]) => prev.filter((m: ChatMessage) => m.id !== progressMsgId));
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
    [backendOnline, currentPatient, addMessage, setMessages, setAgentStatus, setCitations, toastError, toastSuccess]
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
