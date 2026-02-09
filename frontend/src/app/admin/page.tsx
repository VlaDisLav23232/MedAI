"use client";

import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { usePatients } from "@/lib/hooks";
import type { ApiHealthResponse } from "@/lib/api/types";
import {
  Activity,
  Users,
  FileText,
  BarChart3,
  CheckCircle2,
  XCircle,
  Clock,
  Server,
  Cpu,
  TrendingUp,
} from "lucide-react";

// ─── Stat Card ───────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
  color = "brand",
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color?: "brand" | "emerald" | "amber" | "rose";
}) {
  const colorMap = {
    brand: "bg-brand-50 dark:bg-brand-900/20 text-brand-500",
    emerald: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500",
    amber: "bg-amber-50 dark:bg-amber-900/20 text-amber-500",
    rose: "bg-rose-50 dark:bg-rose-900/20 text-rose-500",
  };

  return (
    <div className="flex items-center gap-4 p-5 rounded-2xl glass-card">
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorMap[color]}`}
      >
        <Icon size={22} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">
          {value}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────

export default function AdminPage() {
  const [health, setHealth] = useState<ApiHealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const { data: patientsData } = usePatients();

  useEffect(() => {
    apiClient
      .checkHealth()
      .then((resp) => setHealth("data" in resp ? (resp.data ?? null) : resp as ApiHealthResponse))
      .catch((err) =>
        setHealthError(err instanceof Error ? err.message : "Unreachable")
      );
  }, []);

  const isHealthy = health?.status === "ok";

  return (
    <div className="p-6 lg:p-8 max-w-6xl">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="text-brand-500" size={24} />
          Admin Dashboard
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          System overview and management
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Patients"
          value={patientsData?.count ?? "–"}
          icon={Users}
          color="brand"
        />
        <StatCard
          label="API Status"
          value={isHealthy ? "Online" : healthError ? "Offline" : "…"}
          icon={isHealthy ? CheckCircle2 : XCircle}
          color={isHealthy ? "emerald" : "rose"}
        />
        <StatCard
          label="Tools Registered"
          value={health?.tools_registered.length ?? "–"}
          icon={Cpu}
          color="amber"
        />
        <StatCard
          label="Version"
          value={health?.version ?? "–"}
          icon={Server}
          color="brand"
        />
      </div>

      {/* Section: System Health */}
      <section id="health" className="mb-10">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Activity size={18} className="text-brand-500" />
          System Health
        </h2>
        <div className="rounded-2xl glass-card p-6">
          {healthError ? (
            <div className="flex items-center gap-3 text-rose-600 dark:text-rose-400">
              <XCircle size={20} />
              <div>
                <p className="font-medium">Backend unreachable</p>
                <p className="text-xs text-gray-500">{healthError}</p>
              </div>
            </div>
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 size={18} />
                <span className="font-medium">All systems operational</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                <div className="text-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Status:{" "}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {health.status}
                  </span>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Debug:{" "}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {health.debug ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>
              {health.tools_registered.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    Registered Tools
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {health.tools_registered.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-1 rounded-md bg-gray-100 dark:bg-surface-dark-3 text-xs font-mono text-gray-700 dark:text-gray-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500 animate-pulse">
              Checking health…
            </p>
          )}
        </div>
      </section>

      {/* Section: Patient Management */}
      <section id="patients" className="mb-10">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Users size={18} className="text-brand-500" />
          Patient Management
        </h2>
        <div className="rounded-2xl glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Total patients in system
            </p>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {patientsData?.count ?? "–"}
            </span>
          </div>
          {patientsData?.patients && patientsData.patients.length > 0 && (
            <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Recent Patients
              </p>
              <div className="space-y-2">
                {patientsData.patients.slice(0, 5).map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between py-1.5 text-sm"
                  >
                    <span className="font-medium text-gray-900 dark:text-white">
                      {p.name}
                    </span>
                    <span className="text-xs text-gray-400">{p.id}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Section: Reports */}
      <section id="reports" className="mb-10">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <FileText size={18} className="text-brand-500" />
          Report Audit
        </h2>
        <div className="rounded-2xl glass-card p-6">
          <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <Clock size={16} />
            <p className="text-sm">
              Report audit features will show aggregated report data when the
              backend is fully connected. Connect the analytics endpoint to
              populate this section.
            </p>
          </div>
        </div>
      </section>

      {/* Section: Usage */}
      <section id="usage">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <TrendingUp size={18} className="text-brand-500" />
          Usage Statistics
        </h2>
        <div className="rounded-2xl glass-card p-6">
          <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <Clock size={16} />
            <p className="text-sm">
              Usage analytics will display API call counts, response times, and
              model usage once the analytics backend endpoint is available.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
