"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiClient } from "@/lib/api/client";
import type {
  ApiUser,
  ApiLoginRequest,
  ApiRegisterRequest,
} from "@/lib/api/types";
import { STORAGE_KEYS, ROUTES } from "@/lib/constants";

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
  const router = useRouter();
  const pathname = usePathname();

  // Wire up the 401 callback so any API call that gets a 401
  // immediately clears auth state and redirects to login.
  useEffect(() => {
    apiClient.setOnUnauthorized(() => {
      setUser(null);
      // Only redirect if we're not already on an auth page
      const publicPaths = ["/", ROUTES.login, ROUTES.register];
      if (!publicPaths.includes(pathname)) {
        router.push(ROUTES.login);
      }
    });
    return () => apiClient.setOnUnauthorized(null);
  }, [router, pathname]);

  // Hydrate user from localStorage on mount, then validate token
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stored = localStorage.getItem(STORAGE_KEYS.authUser);
        const token = localStorage.getItem(STORAGE_KEYS.authToken);
        if (stored && token) {
          // Optimistically show cached user while we validate
          try {
            const cached = JSON.parse(stored) as ApiUser;
            if (!cancelled) setUser(cached);
          } catch { /* corrupt cache, ignore */ }

          // Validate token against the backend
          const res = await apiClient.getMe();
          if (!cancelled) {
            if (res.data) {
              setUser(res.data);
              localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(res.data));
            } else {
              // Token expired/invalid — clear stale auth
              localStorage.removeItem(STORAGE_KEYS.authToken);
              localStorage.removeItem(STORAGE_KEYS.authUser);
              setUser(null);
            }
          }
        }
      } catch {
        // corrupt storage — ignore
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (req: ApiLoginRequest): Promise<boolean> => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient.login(req);
      if (res.error || !res.data) {
        setError(res.error || "Login failed");
        return false;
      }
      // Store token and user in localStorage
      localStorage.setItem(STORAGE_KEYS.authToken, res.data.access_token);
      localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(res.data.user));
      setUser(res.data.user);
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
          setError(res.error || "Registration failed");
          return false;
        }
        // Store token and user in localStorage
        localStorage.setItem(STORAGE_KEYS.authToken, res.data.access_token);
        localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(res.data.user));
        setUser(res.data.user);
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
    router.push(ROUTES.login);
  }, [router]);

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
