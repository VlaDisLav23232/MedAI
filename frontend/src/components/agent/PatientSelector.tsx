"use client";

import React, { useEffect, useState, useRef } from "react";
import { usePatients } from "@/lib/hooks";
import { useChatStore } from "@/lib/store";
import { mapApiPatient } from "@/lib/api/mappers";
import type { Patient } from "@/lib/types";
import type { ApiPatientSummary } from "@/lib/api/types";
import { User, ChevronDown, Search, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface PatientSelectorProps {
  /** Pre-select this patient ID on mount (from URL ?patientId=). */
  preselectedId?: string;
}

export function PatientSelector({ preselectedId }: PatientSelectorProps) {
  const { data: patientsData, isLoading } = usePatients();
  const currentPatient = useChatStore((s) => s.currentPatient);
  const setCurrentPatient = useChatStore((s) => s.setCurrentPatient);
  const reset = useChatStore((s) => s.reset);

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // Map API patients to domain type
  const patients: Patient[] = React.useMemo(() => {
    if (!patientsData) return [];
    const list: ApiPatientSummary[] = Array.isArray(patientsData)
      ? patientsData
      : (patientsData as { patients?: ApiPatientSummary[] }).patients ?? [];
    return list.map(mapApiPatient);
  }, [patientsData]);

  // Auto-select from URL or first patient
  useEffect(() => {
    if (currentPatient) return;
    if (patients.length === 0) return;

    if (preselectedId) {
      const found = patients.find((p) => p.id === preselectedId);
      if (found) {
        setCurrentPatient(found);
        return;
      }
    }
    // Don't auto-select — let the user choose explicitly
  }, [patients, preselectedId, currentPatient, setCurrentPatient]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = patients.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.medical_record_number.toLowerCase().includes(search.toLowerCase())
  );

  function selectPatient(p: Patient) {
    if (currentPatient?.id !== p.id) {
      // Switching patient — reset chat
      reset();
      setCurrentPatient(p);
    }
    setOpen(false);
    setSearch("");
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-2 px-2.5 py-1.5 rounded-lg border transition text-sm",
          currentPatient
            ? "border-brand-200 dark:border-brand-800 bg-brand-50/50 dark:bg-brand-900/20 text-gray-900 dark:text-white"
            : "border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400"
        )}
      >
        <div className="w-6 h-6 rounded-md bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center shrink-0">
          <User size={12} className="text-brand-600 dark:text-brand-400" />
        </div>
        {currentPatient ? (
          <div className="text-left">
            <span className="text-xs font-semibold block leading-none">
              {currentPatient.name}
            </span>
            <span className="text-[10px] text-gray-400">
              {currentPatient.medical_record_number}
            </span>
          </div>
        ) : (
          <span className="text-xs font-medium">
            {isLoading ? "Loading…" : "Select Patient"}
          </span>
        )}
        <ChevronDown
          size={14}
          className={cn("transition-transform text-gray-400", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 overflow-hidden">
          {/* Search */}
          <div className="p-2 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-surface-dark-3">
              <Search size={14} className="text-gray-400 shrink-0" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search patients…"
                className="flex-1 bg-transparent text-xs text-gray-900 dark:text-white placeholder-gray-400 outline-none"
                autoFocus
              />
            </div>
          </div>

          {/* List */}
          <div className="max-h-60 overflow-y-auto p-1">
            {filtered.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">
                {isLoading ? "Loading patients…" : "No patients found"}
              </p>
            ) : (
              filtered.map((p) => (
                <button
                  key={p.id}
                  onClick={() => selectPatient(p)}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition",
                    currentPatient?.id === p.id
                      ? "bg-brand-50 dark:bg-brand-900/20"
                      : "hover:bg-gray-50 dark:hover:bg-surface-dark-3"
                  )}
                >
                  <div className="w-7 h-7 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center shrink-0">
                    <User size={13} className="text-brand-600 dark:text-brand-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-semibold text-gray-900 dark:text-white block truncate">
                      {p.name}
                    </span>
                    <span className="text-[10px] text-gray-400 block">
                      {p.medical_record_number} · {p.gender} · DOB {p.dob}
                    </span>
                  </div>
                  {currentPatient?.id === p.id && (
                    <Check size={14} className="text-brand-600 dark:text-brand-400 shrink-0" />
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
