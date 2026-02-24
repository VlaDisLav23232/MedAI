/* ──────────────────────────────────────────────────────────────
 *  React Query hooks — data fetching for backend API
 * ────────────────────────────────────────────────────────────── */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  ApiPatientListResponse,
  ApiPatientSummary,
  ApiPatientTimelineResponse,
  ApiCaseAnalysisResponse,
  ApiCreatePatientRequest,
  ApiReportApprovalRequest,
  ApiReportApprovalResponse,
} from "@/lib/api/types";

// ── Patients ────────────────────────────────────────────────

export function usePatients() {
  return useQuery<ApiPatientListResponse>({
    queryKey: ["patients"],
    queryFn: async () => {
      const res = await apiClient.get<ApiPatientListResponse>("/api/v1/patients");
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
  });
}

export function usePatient(id: string | undefined) {
  return useQuery<ApiPatientSummary>({
    queryKey: ["patient", id],
    enabled: !!id,
    queryFn: async () => {
      const res = await apiClient.get<ApiPatientSummary>(`/api/v1/patients/${id}`);
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation<ApiPatientSummary, Error, ApiCreatePatientRequest>({
    mutationFn: async (req) => {
      const res = await apiClient.post<ApiPatientSummary>("/api/v1/patients", req);
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}

// ── Timeline ────────────────────────────────────────────────

export function useTimeline(patientId: string | undefined) {
  return useQuery<ApiPatientTimelineResponse>({
    queryKey: ["timeline", patientId],
    enabled: !!patientId,
    queryFn: async () => {
      const res = await apiClient.get<ApiPatientTimelineResponse>(
        `/api/v1/patients/${patientId}/timeline`
      );
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
  });
}

// ── Reports ─────────────────────────────────────────────────

export function useReport(id: string | undefined) {
  return useQuery<ApiCaseAnalysisResponse>({
    queryKey: ["report", id],
    enabled: !!id,
    queryFn: async () => {
      const res = await apiClient.get<ApiCaseAnalysisResponse>(
        `/api/v1/cases/reports/${id}`
      );
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
  });
}

export function useApproveReport() {
  const queryClient = useQueryClient();
  return useMutation<
    ApiReportApprovalResponse,
    Error,
    ApiReportApprovalRequest
  >({
    mutationFn: async (req) => {
      const res = await apiClient.post<ApiReportApprovalResponse>(
        `/api/v1/cases/approve`,
        req
      );
      if (res.error) throw new Error(res.error);
      return res.data!;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["report", variables.report_id] });
    },
  });
}
