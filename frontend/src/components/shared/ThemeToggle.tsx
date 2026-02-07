"use client";

import React from "react";
import { useTheme } from "@/providers/ThemeProvider";
import { Sun, Moon, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  const modes = [
    { value: "light" as const, icon: Sun, label: "Light" },
    { value: "dark" as const, icon: Moon, label: "Dark" },
    { value: "system" as const, icon: Monitor, label: "System" },
  ];

  return (
    <div
      className={cn(
        "flex items-center gap-0.5 p-1 rounded-xl bg-gray-100 dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700",
        className
      )}
    >
      {modes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          title={label}
          className={cn(
            "p-1.5 rounded-lg transition-all duration-200",
            theme === value
              ? "bg-white dark:bg-surface-dark-3 shadow-sm text-brand-500"
              : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          )}
        >
          <Icon size={14} />
        </button>
      ))}
    </div>
  );
}
