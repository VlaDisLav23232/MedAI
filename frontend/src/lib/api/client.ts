import type {
  ApiHealthResponse,
  ApiLoginRequest,
  ApiRegisterRequest,
  ApiAuthResponse,
  ApiCaseAnalysisRequest,
  ApiCaseAnalysisResponse,
  ApiUploadResponse,
} from "./types";
import { STORAGE_KEYS } from "@/lib/constants";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

/** Pipeline event received during SSE streaming analysis. */
export interface PipelineEvent {
  type:
    | "pipeline_start"
    | "phase_start"
    | "phase_complete"
    | "tool_start"
    | "tool_complete"
    | "tool_error"
    | "result"
    | "error"
    | "ping";
  ts?: number;
  phase?: string;
  message?: string;
  tool?: string;
  elapsed_s?: number;
  error?: string;
  [key: string]: unknown;
}

/** Callback invoked when a 401 is received — signals session expiry. */
type OnUnauthorizedCallback = () => void;

class ApiClient {
  private baseUrl: string;
  private onUnauthorized: OnUnauthorizedCallback | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /** Register a callback for 401 responses (session expired). */
  setOnUnauthorized(cb: OnUnauthorizedCallback | null) {
    this.onUnauthorized = cb;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      // Get auth token from localStorage
      const token = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEYS.authToken) : null;
      console.log(`[API] ${options.method || 'GET'} ${endpoint}`, {
        hasToken: !!token,
        tokenPrefix: token ? token.substring(0, 20) + '...' : 'none'
      });
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options.headers,
        },
      });

      if (!response.ok) {
        // Detect expired / invalid token → trigger session-expiry flow
        if (response.status === 401 && token) {
          localStorage.removeItem(STORAGE_KEYS.authToken);
          localStorage.removeItem(STORAGE_KEYS.authUser);
          this.onUnauthorized?.();
        }

        let errorMsg: string;
        try {
          const body = await response.json();
          errorMsg = body.detail || body.message || JSON.stringify(body);
        } catch {
          errorMsg = (await response.text()) || `HTTP ${response.status}`;
        }
        return { error: errorMsg };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return { error: error instanceof Error ? error.message : "Unknown error" };
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  // ── Domain methods ──────────────────────────────────────

  async checkHealth(): Promise<ApiResponse<ApiHealthResponse>> {
    return this.get<ApiHealthResponse>("/health");
  }

  async isBackendAvailable(): Promise<boolean> {
    try {
      const res = await this.checkHealth();
      return !!res.data;
    } catch {
      return false;
    }
  }

  async login(req: ApiLoginRequest): Promise<ApiResponse<ApiAuthResponse>> {
    return this.post<ApiAuthResponse>("/api/v1/auth/login", req);
  }

  async register(req: ApiRegisterRequest): Promise<ApiResponse<ApiAuthResponse>> {
    return this.post<ApiAuthResponse>("/api/v1/auth/register", req);
  }

  async getMe(): Promise<ApiResponse<any>> {
    return this.get<any>("/api/v1/auth/me");
  }

  async logout(): Promise<ApiResponse<void>> {
    return this.post<void>("/api/v1/auth/logout");
  }

  async analyzeCase(req: ApiCaseAnalysisRequest): Promise<ApiResponse<ApiCaseAnalysisResponse>> {
    return this.post<ApiCaseAnalysisResponse>("/api/v1/cases/analyze", req);
  }

  /**
   * Stream pipeline progress via SSE while analyzing a case.
   * Calls `onEvent` for each intermediate event and returns the final result.
   */
  async analyzeCaseStream(
    req: ApiCaseAnalysisRequest,
    onEvent: (event: PipelineEvent) => void
  ): Promise<ApiResponse<ApiCaseAnalysisResponse>> {
    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem(STORAGE_KEYS.authToken)
          : null;
      console.log("[API] POST /cases/analyze/stream (SSE)");

      const response = await fetch(`${this.baseUrl}/api/v1/cases/analyze/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(req),
      });

      if (!response.ok) {
        if (response.status === 401 && token) {
          localStorage.removeItem(STORAGE_KEYS.authToken);
          localStorage.removeItem(STORAGE_KEYS.authUser);
          this.onUnauthorized?.();
        }
        let errorMsg: string;
        try {
          const body = await response.json();
          errorMsg = body.detail || body.message || JSON.stringify(body);
        } catch {
          errorMsg = (await response.text()) || `HTTP ${response.status}`;
        }
        return { error: errorMsg };
      }

      // Read SSE stream
      const reader = response.body?.getReader();
      if (!reader) {
        return { error: "No response body for SSE stream" };
      }

      const decoder = new TextDecoder();
      let finalResult: ApiCaseAnalysisResponse | undefined;
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames from buffer
        const frames = buffer.split("\n\n");
        buffer = frames.pop() || ""; // Keep incomplete frame

        for (const frame of frames) {
          if (!frame.trim()) continue;

          let eventType = "message";
          let data = "";

          for (const line of frame.split("\n")) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              data += line.slice(6);
            }
          }

          if (!data) continue;

          try {
            const parsed = JSON.parse(data);

            if (eventType === "result") {
              finalResult = parsed as ApiCaseAnalysisResponse;
            } else if (eventType === "error") {
              return { error: parsed.error || "Pipeline error" };
            } else if (eventType !== "ping") {
              onEvent({ type: eventType as PipelineEvent["type"], ...parsed });
            }
          } catch {
            console.warn("[SSE] Failed to parse frame:", data);
          }
        }
      }

      if (finalResult) {
        return { data: finalResult };
      }
      return { error: "SSE stream ended without result" };
    } catch (error) {
      console.warn("[SSE] Stream failed, will fall back to sync", error);
      return { error: error instanceof Error ? error.message : "Stream failed" };
    }
  }

  /**
   * Upload files (images, audio, documents) via multipart/form-data.
   * Returns pre-sorted URLs by category.
   */
  async uploadFiles(files: File[]): Promise<ApiResponse<ApiUploadResponse>> {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEYS.authToken) : null;
      console.log(`[API] POST /files/upload (${files.length} files)`, {
        hasToken: !!token,
        files: files.map((f) => `${f.name} (${f.type}, ${(f.size / 1024).toFixed(1)}KB)`),
      });

      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }

      const response = await fetch(`${this.baseUrl}/api/v1/files/upload`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          // NOTE: Do NOT set Content-Type — browser auto-sets multipart boundary
        },
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401 && token) {
          localStorage.removeItem(STORAGE_KEYS.authToken);
          localStorage.removeItem(STORAGE_KEYS.authUser);
          this.onUnauthorized?.();
        }
        const error = await response.text();
        return { error: error || `HTTP ${response.status}` };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return { error: error instanceof Error ? error.message : "Upload failed" };
    }
  }
}

export const apiClient = new ApiClient();
