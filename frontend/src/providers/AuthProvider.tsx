"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { apiClient } from "@/lib/api/client";
import type {
  ApiUser,
  ApiLoginRequest,
  ApiRegisterRequest,
} from "@/lib/api/types";
import { STORAGE_KEYS } from "@/lib/constants";

// ─── Context Shape ───────────────────────────────────────

interface AuthContextValue {
  user: ApiUser | null;
  loading: boolean;
  error: string | null;
  login: (req: ApiLoginRequest) => Promise<boolean>;
  register: (req: ApiRegisterRequest) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Provider ────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Hydrate user from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.authUser);
      if (stored) {
        setUser(JSON.parse(stored) as ApiUser);
      }
    } catch {
      // corrupt storage — ignore
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (req: ApiLoginRequest): Promise<boolean> => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient.login(req);
      if (res.error || !res.data) {
        setError(res.error ?? "Login failed");
        return false;
      }
      const { access_token, user } = res.data;
      localStorage.setItem(STORAGE_KEYS.authToken, access_token);
      localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(user));
      setUser(user);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(
    async (req: ApiRegisterRequest): Promise<boolean> => {
      setError(null);
      setLoading(true);
      try {
        const res = await apiClient.register(req);
        if (res.error || !res.data) {
          setError(res.error ?? "Registration failed");
          return false;
        }
        const { access_token, user } = res.data;
        localStorage.setItem(STORAGE_KEYS.authToken, access_token);
        localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(user));
        setUser(user);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Registration failed");
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const logout = useCallback(() => {
    apiClient.logout();
    localStorage.removeItem(STORAGE_KEYS.authToken);
    localStorage.removeItem(STORAGE_KEYS.authUser);
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{ user, loading, error, login, register, logout, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
