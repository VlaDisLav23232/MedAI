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
  X,
  Save,
} from "lucide-react";

type Verdict = "pending" | "approved" | "rejected" | "edited";

export interface ReportEdits {
  diagnosis?: string;
  evidence_summary?: string;
  plan?: string[];
  timeline_impact?: string;
}

interface ApprovalBarProps {
  status: Verdict;
  onApprove: (notes?: string) => void;
  onReject: (notes?: string) => void;
  onEditApprove: (edits: ReportEdits, notes?: string) => void;
  /** Called when the user wants to revise a decision (re-open for review). */
  onRevise?: () => void;
  /** Current report values to pre-fill edit form */
  currentReport?: {
    diagnosis: string;
    evidence_summary: string;
    plan: string[];
    timeline_impact: string;
  };
  loading?: boolean;
  className?: string;
}

export function ApprovalBar({
  status,
  onApprove,
  onReject,
  onEditApprove,
  onRevise,
  currentReport,
  loading = false,
  className,
}: ApprovalBarProps) {
  const [notes, setNotes] = useState("");
  const [showNotes, setShowNotes] = useState(false);
  const [editing, setEditing] = useState(false);

  // Edit-mode state, pre-filled from current report
  const [editDiagnosis, setEditDiagnosis] = useState(currentReport?.diagnosis ?? "");
  const [editEvidence, setEditEvidence] = useState(currentReport?.evidence_summary ?? "");
  const [editPlan, setEditPlan] = useState(currentReport?.plan?.join("\n") ?? "");
  const [editTimelineImpact, setEditTimelineImpact] = useState(currentReport?.timeline_impact ?? "");

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

  const handleStartEdit = () => {
    // Re-initialize from latest report values
    setEditDiagnosis(currentReport?.diagnosis ?? "");
    setEditEvidence(currentReport?.evidence_summary ?? "");
    setEditPlan(currentReport?.plan?.join("\n") ?? "");
    setEditTimelineImpact(currentReport?.timeline_impact ?? "");
    setEditing(true);
  };

  const handleSubmitEdit = () => {
    const edits: ReportEdits = {};
    if (editDiagnosis !== currentReport?.diagnosis) edits.diagnosis = editDiagnosis;
    if (editEvidence !== currentReport?.evidence_summary) edits.evidence_summary = editEvidence;
    const planLines = editPlan.split("\n").map(s => s.trim()).filter(Boolean);
    if (JSON.stringify(planLines) !== JSON.stringify(currentReport?.plan)) edits.plan = planLines;
    if (editTimelineImpact !== currentReport?.timeline_impact) edits.timeline_impact = editTimelineImpact;
    onEditApprove(edits, notes || undefined);
    setEditing(false);
  };

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

        {!editing && (
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
        )}
      </div>

      {/* Notes */}
      {showNotes && !editing && (
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-surface-dark-3">
          <label htmlFor="approval-notes" className="sr-only">Clinical notes or corrections</label>
          <textarea
            id="approval-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add clinical notes or corrections..."
            className="w-full bg-transparent border-none outline-none text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 resize-none"
            rows={3}
          />
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="px-4 py-4 border-b border-gray-100 dark:border-gray-800 bg-brand-50/30 dark:bg-brand-900/5 space-y-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400">
              Edit Report Before Approving
            </h3>
            <button
              onClick={() => setEditing(false)}
              className="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition"
              aria-label="Cancel editing"
            >
              <X size={14} className="text-gray-400" />
            </button>
          </div>

          <div>
            <label htmlFor="edit-diagnosis" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Diagnosis
            </label>
            <input
              id="edit-diagnosis"
              type="text"
              value={editDiagnosis}
              onChange={(e) => setEditDiagnosis(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            />
          </div>

          <div>
            <label htmlFor="edit-evidence" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Evidence Summary
            </label>
            <textarea
              id="edit-evidence"
              value={editEvidence}
              onChange={(e) => setEditEvidence(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 resize-none"
            />
          </div>

          <div>
            <label htmlFor="edit-plan" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Plan <span className="font-normal text-gray-400">(one item per line)</span>
            </label>
            <textarea
              id="edit-plan"
              value={editPlan}
              onChange={(e) => setEditPlan(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 resize-none font-mono"
            />
          </div>

          <div>
            <label htmlFor="edit-impact" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Timeline Impact
            </label>
            <textarea
              id="edit-impact"
              value={editTimelineImpact}
              onChange={(e) => setEditTimelineImpact(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 resize-none"
            />
          </div>

          <div>
            <label htmlFor="edit-notes" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Doctor Notes <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <textarea
              id="edit-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for edits…"
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 rounded-xl text-sm font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitEdit}
              disabled={loading}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition shadow-lg shadow-brand-500/25 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save & Approve
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {status === "pending" && !editing && (
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
            onClick={handleStartEdit}
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

      {status !== "pending" && !editing && (
        <div className="px-4 py-3 space-y-2">
          <p className="text-xs text-gray-500 text-center">
            Decision recorded. This report is now part of the patient record.
          </p>
          {notes && (
            <div className="px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3 border border-gray-100 dark:border-gray-800">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 block mb-0.5">Doctor Notes</span>
              <p className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{notes}</p>
            </div>
          )}
          <div className="flex items-center justify-center gap-3 pt-1">
            <button
              onClick={() => {
                setShowNotes(false);
                setNotes("");
                onRevise?.();
              }}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 text-xs font-medium hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
            >
              <Edit3 size={14} />
              Revise Decision
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
