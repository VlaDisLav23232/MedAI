"use client";

import React, { useState, useRef, useCallback, KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import {
  Send,
  Paperclip,
  Image as ImageIcon,
  AudioLines,
  FileText,
  X,
  Mic,
  Square,
} from "lucide-react";

interface ChatInputProps {
  onSend: (message: string, attachments?: File[]) => void;
  disabled?: boolean;
  className?: string;
  value?: string;
  onValueChange?: (value: string) => void;
}

/** Get browser SpeechRecognition constructor (webkit-prefixed or standard). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getSpeechRecognition(): (new () => any) | null {
  if (typeof window === "undefined") return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const W = window as any;
  return W.SpeechRecognition || W.webkitSpeechRecognition || null;
}

export function ChatInput({ onSend, disabled, className, value: externalValue, onValueChange }: ChatInputProps) {

  const [text, setText] = useState("");
  const isControlled = externalValue !== undefined;
  const currentText = isControlled ? externalValue : text;
  const [files, setFiles] = useState<File[]>([]);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (!currentText.trim() && files.length === 0) return;
    onSend(currentText.trim(), files.length > 0 ? files : undefined);
    if (isControlled) {
      onValueChange?.("");
    } else {
      setText("");
    }
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  };

  const handleFileSelect = (accept: string) => {
    if (fileInputRef.current) {
      fileInputRef.current.accept = accept;
      fileInputRef.current.click();
    }
    setShowAttachMenu(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith("image/")) return ImageIcon;
    if (file.type.startsWith("audio/")) return AudioLines;
    return FileText;
  };

  // ── Voice input via Web Speech API ──────────────────────

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const startRecording = useCallback(() => {
    const SRConstructor = getSpeechRecognition();
    if (!SRConstructor) {
      alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    const recognition = new SRConstructor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let finalTranscript = "";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      // Update text area with final + interim results
      const updateFn = isControlled ? onValueChange : setText;
      if (updateFn) {
        const base = isControlled ? (externalValue ?? "") : "";
        const prefix = base.trim() ? base.trim() + " " : "";
        updateFn(prefix + finalTranscript + interim);
      }
      // Auto-resize textarea
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
          textareaRef.current.style.height =
            Math.min(textareaRef.current.scrollHeight, 160) + "px";
        }
      }, 0);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      if (event.error !== "aborted") {
        alert(`Speech recognition error: ${event.error}. Please try again.`);
      }
      setIsRecording(false);
      recognitionRef.current = null;
    };

    recognition.onend = () => {
      setIsRecording(false);
      setIsTranscribing(false);
      recognitionRef.current = null;
    };

    recognition.start();
    recognitionRef.current = recognition;
    setIsRecording(true);
    setIsTranscribing(false);
  }, [isControlled, externalValue, onValueChange]);

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
  }, []);

  const handleMicToggle = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  return (
    <div className={cn("relative", className)}>
      {/* File previews */}
      {files.length > 0 && (
        <div className="flex gap-2 px-4 pb-2 flex-wrap">
          {files.map((file, i) => {
            const Icon = getFileIcon(file);
            return (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 text-sm"
              >
                <Icon size={14} className="text-brand-500" />
                <span className="text-xs text-gray-700 dark:text-gray-300 max-w-[120px] truncate">
                  {file.name}
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="p-0.5 rounded hover:bg-brand-100 dark:hover:bg-brand-800 transition"
                >
                  <X size={12} className="text-gray-400" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Input bar */}
      <div
        className={cn(
          "flex items-end gap-2 px-4 py-3",
          "bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700",
          "rounded-2xl transition-all duration-200",
          "focus-within:ring-2 focus-within:ring-brand-500/20 focus-within:border-brand-400 dark:focus-within:border-brand-600",
          "neo-shadow"
        )}
      >
        {/* Attach button */}
        <div className="relative">
          <button
            onClick={() => setShowAttachMenu(!showAttachMenu)}
            className="p-2 rounded-xl text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition"
            aria-label="Attach file"
            aria-expanded={showAttachMenu}
            aria-haspopup="menu"
          >
            <Paperclip size={18} />
          </button>

          {showAttachMenu && (
            <div role="menu" className="absolute bottom-full left-0 mb-2 py-2 w-48 bg-white dark:bg-surface-dark-2 rounded-xl border border-gray-200 dark:border-gray-700 neo-shadow-lg z-50">
              <button
                onClick={() => handleFileSelect("image/*")}
                role="menuitem"
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
              >
                <ImageIcon size={16} className="text-accent-cyan" />
                Medical Image
              </button>
              <button
                onClick={() => handleFileSelect("audio/*")}
                role="menuitem"
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
              >
                <AudioLines size={16} className="text-accent-amber" />
                Audio Recording
              </button>
              <button
                onClick={() => handleFileSelect(".pdf,.txt,.doc,.docx")}
                role="menuitem"
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
              >
                <FileText size={16} className="text-accent-violet" />
                Document / Report
              </button>
            </div>
          )}
        </div>

        {/* Textarea */}
        <label htmlFor="chat-input" className="sr-only">Clinical case description</label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          value={currentText}
          onChange={(e) => {
            if (isControlled) {
              onValueChange?.(e.target.value);
            } else {
              setText(e.target.value);
            }
          }}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Describe the clinical case or ask a question..."
          disabled={disabled}
          rows={1}
          className={cn(
            "flex-1 resize-none bg-transparent border-none outline-none",
            "text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500",
            "leading-relaxed py-1",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        />

        {/* Voice button */}
        <button
          onClick={handleMicToggle}
          disabled={disabled || isTranscribing}
          className={cn(
            "p-2 rounded-xl transition-all duration-200",
            isRecording
              ? "text-red-500 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 animate-pulse"
              : isTranscribing
                ? "text-amber-500 bg-amber-50 dark:bg-amber-900/20 opacity-70 cursor-wait"
                : "text-gray-400 hover:text-accent-amber hover:bg-amber-50 dark:hover:bg-amber-900/20"
          )}
          aria-label={isRecording ? "Stop recording" : isTranscribing ? "Transcribing…" : "Start voice input"}
          title={isRecording ? "Click to stop recording" : isTranscribing ? "Transcribing…" : "Voice input (Speech-to-Text)"}
        >
          {isRecording ? <Square size={18} /> : <Mic size={18} />}
        </button>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || (!currentText.trim() && files.length === 0)}
          aria-label="Send message"
          className={cn(
            "p-2.5 rounded-xl transition-all duration-200",
            currentText.trim() || files.length > 0
              ? "bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25"
              : "bg-gray-100 dark:bg-surface-dark-3 text-gray-400 cursor-not-allowed"
          )}
        >
          <Send size={16} />
        </button>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
        aria-label="Upload file"
        multiple
      />
    </div>
  );
}
