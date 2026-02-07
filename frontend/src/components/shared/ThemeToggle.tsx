"use client";

import React from "react";
import { useTheme } from "@/providers/ThemeProvider";
import { Sun, Moon, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, resolvedTheme, setTheme } = useTheme();

  const modes = [
    { value: "light" as const, icon: Sun, label: "Light" },
    { value: "dark" as const, icon: Moon, label: "Dark" },
    { value: "system" as const, icon: Monitor, label: "System" },
  ];

  const getTooltip = (value: typeof theme, label: string): string => {
    if (value === "system") {
      return `${label} (${resolvedTheme === "dark" ? "Dark" : "Light"})`;
    }
    return label;
  };

  return (
    <div
      className={cn(
        "flex items-center gap-0.5 p-1 rounded-xl bg-gray-100 dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-700",
        className
      )}
      role="radiogroup"
      aria-label="Color theme"
    >
      {modes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          title={getTooltip(value, label)}
          aria-label={getTooltip(value, label)}
          aria-pressed={theme === value}
          role="radio"
          aria-checked={theme === value}
          className={cn(
            "relative p-1.5 rounded-lg transition-all duration-200",
            theme === value
              ? "bg-white dark:bg-surface-dark-3 shadow-sm text-brand-500"
              : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          )}
        >
          <Icon size={14} />
          {theme === "system" && value === "system" && (
            <span className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-[8px] font-medium text-gray-400 whitespace-nowrap">
              {resolvedTheme === "dark" ? "Dark" : "Light"}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
