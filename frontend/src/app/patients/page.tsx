"use client";

import React, { useState, type FormEvent } from "react";
import Link from "next/link";
import { cn, formatDate } from "@/lib/utils";
import { LoadingAnimation } from "@/components/shared/LoadingAnimation";
import { usePatients } from "@/lib/hooks";
import { apiClient } from "@/lib/api/client";
import type { ApiCreatePatientRequest } from "@/lib/api/types";
import { ROUTES } from "@/lib/constants";
import {
  Users,
  Plus,
  Search,
  Clock,
  User,
  ChevronRight,
  AlertCircle,
  X,
} from "lucide-react";

export default function PatientsPage() {
  const { data, loading, error, refetch } = usePatients();
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newDob, setNewDob] = useState("");
  const [newGender, setNewGender] = useState("male");
  const [newMrn, setNewMrn] = useState("");

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreateLoading(true);
    try {
      const req: ApiCreatePatientRequest = {
        name: newName,
        date_of_birth: newDob,
        gender: newGender,
        medical_record_number: newMrn || undefined,
      };
      await apiClient.createPatient(req);
      setShowCreate(false);
      setNewName("");
      setNewDob("");
      setNewGender("male");
      setNewMrn("");
      refetch();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create patient");
    } finally {
      setCreateLoading(false);
    }
  }

  const patients = data?.patients ?? [];
  const filtered = search
    ? patients.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.id.toLowerCase().includes(search.toLowerCase()) ||
          (p.medical_record_number?.toLowerCase().includes(search.toLowerCase()) ?? false)
      )
    : patients;

  return (
    <main className="max-w-5xl mx-auto px-4 py-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="text-brand-500" size={24} />
            Patients
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {loading ? "Loading…" : `${data?.count ?? 0} patients`}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition"
        >
          <Plus size={16} />
          New Patient
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          type="text"
          placeholder="Search by name, ID, or MRN…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <LoadingAnimation label="Loading patients…" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm mb-6">
          <AlertCircle size={16} className="flex-shrink-0" />
          <span>{error}</span>
          <button
            onClick={refetch}
            className="ml-auto text-xs font-medium underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Patient List */}
      {!loading && !error && (
        <div className="space-y-3">
          {filtered.length === 0 && (
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 py-12">
              {search ? "No patients match your search." : "No patients found."}
            </p>
          )}
          {filtered.map((p) => (
            <Link
              key={p.id}
              href={ROUTES.timeline(p.id)}
              className="flex items-center gap-4 p-4 rounded-2xl glass-card hover:neo-shadow transition group"
            >
              <div className="w-10 h-10 rounded-full bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                <User size={18} className="text-brand-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {p.name}
                </p>
                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  <span>{p.id}</span>
                  {p.medical_record_number && (
                    <span>MRN: {p.medical_record_number}</span>
                  )}
                  <span className="inline-flex items-center gap-1">
                    <Clock size={10} />
                    {formatDate(p.created_at)}
                  </span>
                </div>
              </div>
              <ChevronRight
                size={16}
                className="text-gray-400 group-hover:text-brand-500 transition flex-shrink-0"
              />
            </Link>
          ))}
        </div>
      )}

      {/* Create Patient Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-surface-dark border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                New Patient
              </h2>
              <button
                onClick={() => setShowCreate(false)}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-2 transition"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            {createError && (
              <div className="flex items-center gap-2 p-3 mb-4 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm">
                <AlertCircle size={14} />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label
                  htmlFor="patient-name"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Full Name
                </label>
                <input
                  id="patient-name"
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label
                  htmlFor="patient-dob"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Date of Birth
                </label>
                <input
                  id="patient-dob"
                  type="date"
                  required
                  value={newDob}
                  onChange={(e) => setNewDob(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label
                  htmlFor="patient-gender"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Gender
                </label>
                <select
                  id="patient-gender"
                  value={newGender}
                  onChange={(e) => setNewGender(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="patient-mrn"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Medical Record Number (optional)
                </label>
                <input
                  id="patient-mrn"
                  type="text"
                  value={newMrn}
                  onChange={(e) => setNewMrn(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <button
                type="submit"
                disabled={createLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 text-white font-medium text-sm hover:bg-brand-600 transition disabled:opacity-50"
              >
                <Plus size={16} />
                {createLoading ? "Creating…" : "Create Patient"}
              </button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
