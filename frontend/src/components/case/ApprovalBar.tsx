"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  Edit3,
  XCircle,
  MessageSquare,
  ChevronDown,
  Loader2,
} from "lucide-react";

type Verdict = "pending" | "approved" | "rejected" | "edited";

interface ApprovalBarProps {
  status: Verdict;
  onApprove: (notes?: string) => void;
  onReject: (notes?: string) => void;
  onEdit: (notes?: string) => void;
  loading?: boolean;
  className?: string;
}

export function ApprovalBar({
  status,
  onApprove,
  onReject,
  onEdit,
  loading = false,
  className,
}: ApprovalBarProps) {
  const [notes, setNotes] = useState("");
  const [showNotes, setShowNotes] = useState(false);

  const statusDisplay: Record<
    Verdict,
    { label: string; color: string; icon: React.ElementType }
  > = {
    pending: {
      label: "Pending Review",
      color: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800",
      icon: MessageSquare,
    },
    approved: {
      label: "Approved",
      color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
      icon: CheckCircle2,
    },
    rejected: {
      label: "Rejected",
      color: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800",
      icon: XCircle,
    },
    edited: {
      label: "Approved with Edits",
      color: "bg-brand-500/10 text-brand-600 dark:text-brand-400 border-brand-200 dark:border-brand-800",
      icon: Edit3,
    },
  };

  const current = statusDisplay[status];
  const StatusIcon = current.icon;

  return (
    <div
      className={cn(
        "rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark-2 overflow-hidden",
        className
      )}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-gray-900 dark:text-white">
            Doctor&apos;s Decision
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg border text-xs font-medium",
              current.color
            )}
          >
            <StatusIcon size={12} />
            {current.label}
          </span>
        </div>

        <button
          onClick={() => setShowNotes(!showNotes)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
        >
          <MessageSquare size={12} />
          Notes
          <ChevronDown
            size={12}
            className={cn("transition-transform", showNotes && "rotate-180")}
          />
        </button>
      </div>

      {/* Notes */}
      {showNotes && (
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-surface-dark-3">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add clinical notes or corrections..."
            className="w-full bg-transparent border-none outline-none text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 resize-none"
            rows={3}
          />
        </div>
      )}

      {/* Action buttons */}
      {status === "pending" && (
        <div className="flex items-center justify-end gap-3 px-4 py-3">
          <button
            onClick={() => onReject(notes || undefined)}
            disabled={loading}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/10 text-rose-600 dark:text-rose-400 text-sm font-medium hover:bg-rose-100 dark:hover:bg-rose-900/20 transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
            Reject
          </button>
          <button
            onClick={() => onEdit(notes || undefined)}
            disabled={loading}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl border border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-900/10 text-brand-600 dark:text-brand-400 text-sm font-medium hover:bg-brand-100 dark:hover:bg-brand-900/20 transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Edit3 size={16} />}
            Edit & Approve
          </button>
          <button
            onClick={() => onApprove(notes || undefined)}
            disabled={loading}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-accent-emerald text-white text-sm font-medium hover:bg-emerald-600 transition shadow-lg shadow-emerald-500/25 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
            Approve
          </button>
        </div>
      )}

      {status !== "pending" && (
        <div className="px-4 py-3 text-center">
          <p className="text-xs text-gray-500">
            Decision recorded. This report is now part of the patient record.
          </p>
        </div>
      )}
    </div>
  );
}
