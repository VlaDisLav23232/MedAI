"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { ROUTES } from "@/lib/constants";

const PUBLIC_PATHS = [
  "/",
  ROUTES.login,
  ROUTES.register,
];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user && !PUBLIC_PATHS.includes(pathname)) {
      router.push(ROUTES.login);
    }
  }, [user, loading, pathname, router]);

  // Show loading or nothing while checking auth
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Render children if authenticated or on public page
  if (user || PUBLIC_PATHS.includes(pathname)) {
    return <>{children}</>;
  }

  // Don't render anything while redirecting
  return null;
}
