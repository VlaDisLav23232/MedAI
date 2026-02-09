"use client";

import React from "react";
import Link from "next/link";
import { cn, formatTime } from "@/lib/utils";
import type { ChatMessage as ChatMessageType, ToolResult } from "@/lib/types";
import {
  User,
  Bot,
  Image as ImageIcon,
  AudioLines,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  BookOpen,
} from "lucide-react";

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (citationId: string) => void;
}

/**
 * Strip JSON / code-block artifacts from AI-generated markdown content.
 * Removes ```json blocks, raw JSON objects/arrays, and cleans up leftover markers.
 */
function cleanMarkdownContent(text: string): string {
  let cleaned = text;

  // Remove fenced code blocks with optional language tag
  cleaned = cleaned.replace(/```[\w]*\s*\n?[\s\S]*?```/g, "");

  // Remove standalone raw JSON objects that look like AI data dumps
  cleaned = cleaned.replace(
    /\{[\s\S]*?"(?:reasoning_chain|evidence_citations|plan_suggestions|contraindication_flags|tool_timings|diagnosis|confidence|assessment|findings|timeline_context|specialist_outputs)"[\s\S]*?\}/g,
    ""
  );

  // Remove JSON arrays that look like reasoning chains
  cleaned = cleaned.replace(
    /\[[\s\S]*?\{[\s\S]*?"(?:step|thought|action|observation)"[\s\S]*?\}[\s\S]*?\]/g,
    ""
  );

  // Remove leftover empty fenced code blocks
  cleaned = cleaned.replace(/```\s*```/g, "");

  // Collapse excessive blank lines
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  return cleaned.trim();
}

function ToolResultItem({ result }: { result: ToolResult }) {
  const statusIcon = {
    running: <Loader2 size={12} className="animate-spin text-brand-500" />,
    complete: <CheckCircle2 size={12} className="text-accent-emerald" />,
    error: <AlertCircle size={12} className="text-accent-rose" />,
  }[result.status];

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg text-xs",
        "bg-gray-50 dark:bg-surface-dark-3 border border-gray-100 dark:border-gray-700"
      )}
    >
      {statusIcon}
      <span className="font-medium text-gray-700 dark:text-gray-300">
        {result.tool}
      </span>
      {result.duration_ms && (
        <span className="text-gray-400 ml-auto flex items-center gap-1">
          <Clock size={10} />
          {(result.duration_ms / 1000).toFixed(1)}s
        </span>
      )}
      {result.summary && (
        <span className="text-gray-500 dark:text-gray-400 ml-2 truncate max-w-[200px]">
          — {result.summary}
        </span>
      )}
    </div>
  );
}

/** Safely render inline markdown (bold, links, emoji) without dangerouslySetInnerHTML */
function renderInline(text: string, isUser: boolean): React.ReactNode {
  // First handle markdown links [text](url)
  const linkParts = text.split(/(\[.*?\]\(.*?\))/g);
  return linkParts.map((segment, li) => {
    const linkMatch = segment.match(/\[(.*?)\]\((.*?)\)/);
    if (linkMatch) {
      const [, linkText, linkHref] = linkMatch;
      return (
        <Link
          key={`link-${li}`}
          href={linkHref}
          className={cn(
            "inline-flex items-center gap-1 font-semibold underline underline-offset-2",
            isUser ? "text-white/90 hover:text-white" : "text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
          )}
        >
          {linkText}
        </Link>
      );
    }

    // Split on **bold** markers
    const parts = segment.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={`${li}-${i}`} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      // Highlight certain emoji
      return part.split(/(✅|↑)/g).map((seg, j) => {
        if (seg === "✅") return <span key={`${li}-${i}-${j}`} className="text-accent-emerald">✅</span>;
        if (seg === "↑") return <span key={`${li}-${i}-${j}`} className="text-accent-rose">↑</span>;
        return <React.Fragment key={`${li}-${i}-${j}`}>{seg}</React.Fragment>;
      });
    });
  });
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <span className="text-xs text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-surface-dark-2 px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex gap-3 animate-slide-up",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0",
          isUser
            ? "bg-brand-500 text-white"
            : "bg-gradient-to-br from-accent-cyan to-brand-500 text-white"
        )}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Message content */}
      <div className={cn("flex flex-col max-w-[75%]", isUser ? "items-end" : "items-start")}>
        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex gap-2 mb-2 flex-wrap">
            {message.attachments.map((att) => (
              <div
                key={att.id}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800"
              >
                {att.type === "image" ? (
                  <ImageIcon size={14} className="text-accent-cyan" />
                ) : att.type === "audio" ? (
                  <AudioLines size={14} className="text-accent-amber" />
                ) : (
                  <FileText size={14} className="text-accent-violet" />
                )}
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  {att.name}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Bubble */}
        <div className={cn(isUser ? "chat-bubble-user" : "chat-bubble-agent", "px-4 py-3")}>
          {/* Tool results */}
          {message.toolResults && message.toolResults.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {message.toolResults.map((result, i) => (
                <ToolResultItem key={i} result={result} />
              ))}
            </div>
          )}

          {/* Text content — safe markdown rendering */}
          <div
            className={cn(
              "text-sm leading-relaxed whitespace-pre-wrap",
              isUser ? "text-white" : "text-gray-800 dark:text-gray-200",
              "[&_h2]:text-base [&_h2]:font-bold [&_h2]:mt-3 [&_h2]:mb-1",
              "[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-2 [&_h3]:mb-1",
              "[&_strong]:font-semibold",
              !isUser && "[&_h2]:text-gray-900 [&_h2]:dark:text-white",
              !isUser && "[&_h3]:text-gray-800 [&_h3]:dark:text-gray-200"
            )}
          >
            {cleanMarkdownContent(message.content).split("\n").map((line, i) => {
              if (line.startsWith("## ")) {
                return <h2 key={i}>{renderInline(line.replace("## ", ""), isUser)}</h2>;
              }
              if (line.startsWith("### ")) {
                return <h3 key={i}>{renderInline(line.replace("### ", ""), isUser)}</h3>;
              }
              if (line.match(/^\d+\.\s/)) {
                return (
                  <div key={i} className="ml-4 flex gap-2">
                    <span className="text-gray-400 flex-shrink-0">{line.match(/^\d+/)![0]}.</span>
                    <span>{renderInline(line.replace(/^\d+\.\s/, ""), isUser)}</span>
                  </div>
                );
              }
              if (line.startsWith("- ")) {
                return (
                  <div key={i} className="ml-4 flex gap-2">
                    <span className="text-brand-500">•</span>
                    <span>{renderInline(line.replace("- ", ""), isUser)}</span>
                  </div>
                );
              }
              if (line.trim() === "") return <br key={i} />;
              return <p key={i}>{renderInline(line, isUser)}</p>;
            })}
          </div>

          {/* Inline citation refs */}
          {message.citations && message.citations.length > 0 && (
            <div className="flex gap-1.5 mt-3 pt-2 border-t border-gray-100 dark:border-gray-700 flex-wrap">
              {message.citations.map((cit) => (
                <button
                  key={cit.id}
                  onClick={() => onCitationClick?.(cit.id)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 text-[10px] font-medium hover:bg-brand-100 dark:hover:bg-brand-900/40 transition"
                >
                  <BookOpen size={10} />
                  {cit.title}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <time
          dateTime={message.timestamp}
          className="text-[10px] text-gray-400 mt-1 px-1"
        >
          {formatTime(message.timestamp)}
        </time>
      </div>
    </div>
  );
}
