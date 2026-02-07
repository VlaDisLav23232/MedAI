"use client";

import React, { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { LoadingAnimation } from "@/components/shared/LoadingAnimation";
import { ROUTES } from "@/lib/constants";

interface ProtectedRouteProps {
  children: ReactNode;
  /** If set, only users with this role can access the page. */
  requiredRole?: "doctor" | "admin" | "nurse";
}

/**
 * Wraps a page that requires authentication.
 * Redirects unauthenticated users to /auth/login.
 */
export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(ROUTES.login);
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingAnimation label="Checking authentication…" />
      </div>
    );
  }

  if (!user) return null; // redirect in progress

  if (requiredRole && user.role !== requiredRole) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Access Denied
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          You need the <strong>{requiredRole}</strong> role to view this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
