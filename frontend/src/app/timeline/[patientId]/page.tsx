"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { cn, formatDate } from "@/lib/utils";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { LoadingAnimation } from "@/components/shared/LoadingAnimation";
import { mockPatient, mockTimelineEvents } from "@/lib/mock-data";
import { apiClient } from "@/lib/api/client";
import type { TimelineEvent } from "@/lib/types";
import {
  ArrowLeft,
  User,
  Calendar,
  Image as ImageIcon,
  FlaskConical,
  Stethoscope,
  Bot,
  Pill,
  Activity,
  Filter,
  ChevronRight,
  ChevronDown,
  AlertCircle,
  Wifi,
  WifiOff,
  FileText,
} from "lucide-react";

// ─── Event Type Config ───────────────────────────────────

const eventTypeConfig: Record<
  string,
  { icon: React.ElementType; color: string; bg: string; label: string }
> = {
  imaging: {
    icon: ImageIcon,
    color: "text-accent-cyan",
    bg: "bg-accent-cyan/10 border-accent-cyan/20",
    label: "Imaging",
  },
  lab: {
    icon: FlaskConical,
    color: "text-accent-violet",
    bg: "bg-accent-violet/10 border-accent-violet/20",
    label: "Lab Result",
  },
  encounter: {
    icon: Stethoscope,
    color: "text-brand-500",
    bg: "bg-brand-500/10 border-brand-500/20",
    label: "Encounter",
  },
  ai_report: {
    icon: Bot,
    color: "text-accent-emerald",
    bg: "bg-accent-emerald/10 border-accent-emerald/20",
    label: "AI Report",
  },
  procedure: {
    icon: Activity,
    color: "text-accent-amber",
    bg: "bg-accent-amber/10 border-accent-amber/20",
    label: "Procedure",
  },
  medication: {
    icon: Pill,
    color: "text-accent-rose",
    bg: "bg-accent-rose/10 border-accent-rose/20",
    label: "Medication",
  },
  note: {
    icon: FileText,
    color: "text-gray-500",
    bg: "bg-gray-100 border-gray-200 dark:bg-gray-800 dark:border-gray-700",
    label: "Note",
  },
  audio: {
    icon: Activity,
    color: "text-accent-amber",
    bg: "bg-accent-amber/10 border-accent-amber/20",
    label: "Audio",
  },
};

const defaultEventConfig = eventTypeConfig.encounter;

type FilterType = "all" | TimelineEvent["event_type"];

// ─── Helpers ─────────────────────────────────────────────

function normalizeEventType(apiType: string): TimelineEvent["event_type"] {
  const known: TimelineEvent["event_type"][] = [
    "imaging",
    "lab",
    "encounter",
    "ai_report",
    "procedure",
    "medication",
  ];
  if (known.includes(apiType as TimelineEvent["event_type"])) {
    return apiType as TimelineEvent["event_type"];
  }
  return "encounter";
}

// ─── Page Component ──────────────────────────────────────

export default function TimelinePage({
  params,
}: {
  params: { patientId: string };
}) {
  const { patientId } = params;
  const [filter, setFilter] = useState<FilterType>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>(mockTimelineEvents);
  const [patient, setPatient] = useState(mockPatient);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<"api" | "mock">("mock");

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [timelineRes, patientRes] = await Promise.all([
          apiClient.getPatientTimeline(patientId),
          apiClient.getPatient(patientId),
        ]);

        if (cancelled) return;

        const mapped: TimelineEvent[] = timelineRes.events.map((e) => ({
          id: e.id,
          patient_id: timelineRes.patient_id,
          date:
            typeof e.date === "string"
              ? e.date
              : new Date(e.date).toISOString(),
          event_type: normalizeEventType(e.event_type),
          summary: e.summary,
          source_id: (e.metadata?.source_id as string) || e.id,
          source_type: e.source_type || "unknown",
          severity:
            (e.metadata?.severity as TimelineEvent["severity"]) || undefined,
        }));

        setEvents(mapped);
        setPatient({
          id: patientRes.id,
          name: patientRes.name,
          dob: patientRes.date_of_birth,
          gender: patientRes.gender as "male" | "female" | "other",
          medical_record_number: patientRes.medical_record_number || "",
        });
        setDataSource("api");
      } catch {
        if (cancelled) return;
        setEvents(mockTimelineEvents);
        setPatient(mockPatient);
        setDataSource("mock");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  // ── Filtering & Grouping ───────────────────────────────

  const allTypes: FilterType[] = [
    "all",
    "imaging",
    "lab",
    "encounter",
    "ai_report",
    "medication",
    "procedure",
  ];

  const filteredEvents = useMemo(
    () =>
      filter === "all"
        ? events
        : events.filter((e) => e.event_type === filter),
    [events, filter]
  );

  const groupedByYear = useMemo(() => {
    return filteredEvents.reduce(
      (acc, event) => {
        const year = new Date(event.date).getFullYear().toString();
        if (!acc[year]) acc[year] = [];
        acc[year].push(event);
        return acc;
      },
      {} as Record<string, TimelineEvent[]>
    );
  }, [filteredEvents]);

  const sortedYears = useMemo(
    () => Object.keys(groupedByYear).sort((a, b) => Number(b) - Number(a)),
    [groupedByYear]
  );

  // ── Loading State ──────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center">
        <div className="text-center">
          <LoadingAnimation
            label="Loading patient timeline…"
            variant="orbital"
          />
          <p className="text-xs text-gray-400 mt-3">
            Fetching longitudinal health records
          </p>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* ── Header ─────────────────────────────────── */}
      <header className="bg-white dark:bg-surface-dark-2 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4 mb-4">
            <Link
              href="/agent"
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition"
              aria-label="Back to co-pilot"
            >
              <ArrowLeft size={18} className="text-gray-400" />
            </Link>
            <div
              className="h-5 w-px bg-gray-200 dark:bg-gray-700"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Calendar
                  size={20}
                  className="text-brand-500"
                  aria-hidden="true"
                />
                Patient Timeline
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Longitudinal health record across all encounters
              </p>
            </div>
          </div>

          {/* Patient info card */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-surface-dark-3 border border-gray-100 dark:border-gray-800">
            <div
              className="w-10 h-10 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center"
              aria-hidden="true"
            >
              <User
                size={18}
                className="text-brand-600 dark:text-brand-400"
              />
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white block">
                {patient.name}
              </span>
              <span className="text-xs text-gray-400">
                {patient.medical_record_number} · DOB:{" "}
                <time dateTime={patient.dob}>{formatDate(patient.dob)}</time>{" "}
                · {patient.gender}
              </span>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-gray-400">
                {events.length} event
                {events.length !== 1 ? "s" : ""} recorded
              </span>
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
                  dataSource === "api"
                    ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400"
                )}
                title={
                  dataSource === "api"
                    ? "Connected to backend API"
                    : "Using demo data (backend unavailable)"
                }
              >
                {dataSource === "api" ? (
                  <Wifi size={10} />
                ) : (
                  <WifiOff size={10} />
                )}
                {dataSource === "api" ? "Live" : "Demo"}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Error banner ──────────────────────────── */}
      {error && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800">
            <AlertCircle
              size={14}
              className="text-accent-rose flex-shrink-0"
            />
            <p className="text-xs text-rose-700 dark:text-rose-400">{error}</p>
          </div>
        </div>
      )}

      {/* ── Filter bar ────────────────────────────── */}
      <nav
        className="sticky top-16 z-20 bg-white/80 dark:bg-surface-dark/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800"
        aria-label="Timeline event type filters"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5">
          <div
            className="flex items-center gap-2 overflow-x-auto"
            role="tablist"
          >
            <Filter
              size={14}
              className="text-gray-400 flex-shrink-0"
              aria-hidden="true"
            />
            {allTypes.map((type) => {
              const isAll = type === "all";
              const config = isAll
                ? null
                : eventTypeConfig[type as TimelineEvent["event_type"]];
              const Icon = config?.icon;
              const count = isAll
                ? events.length
                : events.filter((e) => e.event_type === type).length;

              return (
                <button
                  key={type}
                  role="tab"
                  aria-selected={filter === type}
                  onClick={() => setFilter(type)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition",
                    filter === type
                      ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-800"
                      : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-dark-2"
                  )}
                >
                  {Icon && <Icon size={12} aria-hidden="true" />}
                  {isAll ? "All" : config?.label}
                  <span className="text-[10px] opacity-60">({count})</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* ── Timeline content ──────────────────────── */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {sortedYears.map((year) => (
          <section
            key={year}
            className="mb-10"
            aria-label={`Events from ${year}`}
          >
            <div className="flex items-center gap-3 mb-4">
              <time
                dateTime={year}
                className="text-2xl font-extrabold text-gray-200 dark:text-gray-800 font-mono"
              >
                {year}
              </time>
              <div
                className="flex-1 h-px bg-gray-200 dark:bg-gray-800"
                aria-hidden="true"
              />
              <span className="text-xs text-gray-400">
                {groupedByYear[year].length} event
                {groupedByYear[year].length !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="relative">
              <div
                className="absolute left-[23px] top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-800"
                aria-hidden="true"
              />

              <ol className="space-y-4 list-none" role="list">
                {groupedByYear[year].map((event, i) => {
                  const config =
                    eventTypeConfig[event.event_type] || defaultEventConfig;
                  const Icon = config.icon;
                  const isExpanded = expandedId === event.id;

                  return (
                    <li
                      key={event.id}
                      className="relative flex items-start gap-4 group animate-slide-up"
                      style={{ animationDelay: `${i * 0.05}s` }}
                    >
                      <div
                        className="relative z-10 flex-shrink-0"
                        aria-hidden="true"
                      >
                        <div
                          className={cn(
                            "w-[46px] h-[46px] rounded-xl flex items-center justify-center border transition-all",
                            config.bg,
                            "group-hover:scale-110"
                          )}
                        >
                          <Icon size={18} className={config.color} />
                        </div>
                      </div>

                      <article
                        className={cn(
                          "flex-1 rounded-xl bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 neo-shadow transition-all duration-200",
                          isExpanded
                            ? "neo-shadow-lg ring-1 ring-brand-500/10"
                            : "group-hover:neo-shadow-lg"
                        )}
                      >
                        <button
                          onClick={() =>
                            setExpandedId(isExpanded ? null : event.id)
                          }
                          className="w-full p-4 text-left"
                          aria-expanded={isExpanded}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                                  {config.label}
                                </span>
                                {event.severity &&
                                  event.severity !== "normal" && (
                                    <SeverityBadge severity={event.severity} />
                                  )}
                              </div>
                              <p className="text-sm font-medium text-gray-900 dark:text-white">
                                {event.summary}
                              </p>
                            </div>

                            <div className="flex items-center gap-2 flex-shrink-0">
                              <time
                                dateTime={event.date}
                                className="text-xs text-gray-400 font-mono"
                              >
                                {formatDate(event.date)}
                              </time>
                              <ChevronDown
                                size={14}
                                className={cn(
                                  "text-gray-300 dark:text-gray-600 transition-transform duration-200",
                                  isExpanded
                                    ? "rotate-180 text-brand-500"
                                    : ""
                                )}
                              />
                            </div>
                          </div>
                        </button>

                        {/* Expanded details */}
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-0 border-t border-gray-100 dark:border-gray-800 animate-fade-in">
                            <div className="mt-3 space-y-2">
                              <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span>
                                  Source:{" "}
                                  <span className="font-mono text-gray-400">
                                    {event.source_type}
                                  </span>
                                </span>
                                <span>
                                  ID:{" "}
                                  <span className="font-mono text-gray-400">
                                    {event.source_id}
                                  </span>
                                </span>
                              </div>
                              {event.event_type === "ai_report" && (
                                <Link
                                  href={`/case/${event.source_id}`}
                                  className="inline-flex items-center gap-1 text-xs text-brand-500 hover:text-brand-600 font-medium mt-2"
                                >
                                  View Full AI Report
                                  <ChevronRight size={12} />
                                </Link>
                              )}
                            </div>
                          </div>
                        )}
                      </article>
                    </li>
                  );
                })}
              </ol>
            </div>
          </section>
        ))}

        {filteredEvents.length === 0 && (
          <div className="text-center py-16 text-gray-400" role="status">
            <Calendar
              size={40}
              className="mx-auto mb-3 opacity-40"
              aria-hidden="true"
            />
            <p className="text-sm">No events found for this filter</p>
          </div>
        )}
      </main>
    </div>
  );
}
