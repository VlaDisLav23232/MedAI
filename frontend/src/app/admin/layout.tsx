"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import {
  LayoutDashboard,
  Activity,
  Users,
  FileText,
  BarChart3,
  ChevronLeft,
} from "lucide-react";

const sidebarLinks = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, href: "/admin" },
  { id: "health", label: "System Health", icon: Activity, href: "/admin#health" },
  { id: "patients", label: "Patients", icon: Users, href: "/admin#patients" },
  { id: "reports", label: "Reports", icon: FileText, href: "/admin#reports" },
  { id: "usage", label: "Usage Stats", icon: BarChart3, href: "/admin#usage" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="flex min-h-screen pt-16">
        {/* Sidebar */}
        <aside
          className={cn(
            "fixed top-16 left-0 bottom-0 z-30 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark-2 transition-all duration-300 flex flex-col",
            collapsed ? "w-16" : "w-56"
          )}
        >
          <div className="flex-1 py-4">
            <nav className="space-y-1 px-2">
              {sidebarLinks.map(({ id, label, icon: Icon, href }) => {
                const isActive = pathname === href || (id === "overview" && pathname === "/admin");
                return (
                  <Link
                    key={id}
                    href={href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition",
                      collapsed && "justify-center",
                      isActive
                        ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400"
                        : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-surface-dark-3"
                    )}
                    title={collapsed ? label : undefined}
                  >
                    <Icon size={18} />
                    {!collapsed && <span>{label}</span>}
                  </Link>
                );
              })}
            </nav>
          </div>

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center p-3 border-t border-gray-200 dark:border-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <ChevronLeft
              size={16}
              className={cn("transition-transform", collapsed && "rotate-180")}
            />
          </button>
        </aside>

        {/* Main content */}
        <main
          className={cn(
            "flex-1 transition-all duration-300",
            collapsed ? "ml-16" : "ml-56"
          )}
        >
          {children}
        </main>
      </div>
    </ProtectedRoute>
  );
}
