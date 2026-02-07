"use client";

import React, { useState } from "react";
import Link from "next/link";
import { cn, formatDate } from "@/lib/utils";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { mockPatient, mockTimelineEvents } from "@/lib/mock-data";
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
} from "lucide-react";

const eventTypeConfig: Record<
  TimelineEvent["event_type"],
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
};

type FilterType = "all" | TimelineEvent["event_type"];

export default function TimelinePage() {
  const [filter, setFilter] = useState<FilterType>("all");

  const allTypes: FilterType[] = [
    "all",
    "imaging",
    "lab",
    "encounter",
    "ai_report",
    "medication",
    "procedure",
  ];

  const filteredEvents =
    filter === "all"
      ? mockTimelineEvents
      : mockTimelineEvents.filter((e) => e.event_type === filter);

  // Group by year
  const groupedByYear = filteredEvents.reduce(
    (acc, event) => {
      const year = new Date(event.date).getFullYear().toString();
      if (!acc[year]) acc[year] = [];
      acc[year].push(event);
      return acc;
    },
    {} as Record<string, TimelineEvent[]>
  );

  const sortedYears = Object.keys(groupedByYear).sort((a, b) => Number(b) - Number(a));

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* Header */}
      <div className="bg-white dark:bg-surface-dark-2 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4 mb-4">
            <Link
              href="/agent"
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-3 transition"
            >
              <ArrowLeft size={18} className="text-gray-400" />
            </Link>
            <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Calendar size={20} className="text-brand-500" />
                Patient Timeline
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Longitudinal health record across all encounters
              </p>
            </div>
          </div>

          {/* Patient info */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-surface-dark-3 border border-gray-100 dark:border-gray-800">
            <div className="w-10 h-10 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
              <User size={18} className="text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white block">
                {mockPatient.name}
              </span>
              <span className="text-xs text-gray-400">
                {mockPatient.medical_record_number} · DOB: {formatDate(mockPatient.dob)} ·{" "}
                {mockPatient.gender}
              </span>
            </div>
            <div className="ml-auto text-xs text-gray-400">
              {mockTimelineEvents.length} events recorded
            </div>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="sticky top-16 z-20 bg-white/80 dark:bg-surface-dark/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5">
          <div className="flex items-center gap-2 overflow-x-auto">
            <Filter size={14} className="text-gray-400 flex-shrink-0" />
            {allTypes.map((type) => {
              const isAll = type === "all";
              const config = isAll ? null : eventTypeConfig[type as TimelineEvent["event_type"]];
              const Icon = config?.icon;
              const count = isAll
                ? mockTimelineEvents.length
                : mockTimelineEvents.filter((e) => e.event_type === type).length;

              return (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition",
                    filter === type
                      ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-800"
                      : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-dark-2"
                  )}
                >
                  {Icon && <Icon size={12} />}
                  {isAll ? "All" : config?.label}
                  <span className="text-[10px] opacity-60">({count})</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Timeline content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {sortedYears.map((year) => (
          <div key={year} className="mb-10">
            {/* Year header */}
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl font-extrabold text-gray-200 dark:text-gray-800 font-mono">
                {year}
              </span>
              <div className="flex-1 h-px bg-gray-200 dark:bg-gray-800" />
              <span className="text-xs text-gray-400">
                {groupedByYear[year].length} event(s)
              </span>
            </div>

            {/* Events */}
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-[23px] top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-800" />

              <div className="space-y-4">
                {groupedByYear[year].map((event, i) => {
                  const config = eventTypeConfig[event.event_type];
                  const Icon = config.icon;

                  return (
                    <div
                      key={event.id}
                      className="relative flex items-start gap-4 group animate-slide-up"
                      style={{ animationDelay: `${i * 0.05}s` }}
                    >
                      {/* Dot on timeline */}
                      <div className="relative z-10 flex-shrink-0">
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

                      {/* Event card */}
                      <div className="flex-1 p-4 rounded-xl bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 neo-shadow group-hover:neo-shadow-lg transition-all duration-200">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                                {config.label}
                              </span>
                              {event.severity && event.severity !== "normal" && (
                                <SeverityBadge severity={event.severity} />
                              )}
                            </div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                              {event.summary}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-xs text-gray-400 font-mono">
                              {formatDate(event.date)}
                            </span>
                            <ChevronRight
                              size={14}
                              className="text-gray-300 dark:text-gray-600 group-hover:text-brand-500 transition"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ))}

        {filteredEvents.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <Calendar size={40} className="mx-auto mb-3 opacity-40" />
            <p className="text-sm">No events found for this filter</p>
          </div>
        )}
      </div>
    </div>
  );
}
