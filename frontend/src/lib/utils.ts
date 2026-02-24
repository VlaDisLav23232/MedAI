import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

export function formatTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function getConfidenceBg(confidence: number): string {
  if (confidence >= 0.8) {
    return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
  }
  if (confidence >= 0.5) {
    return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
  }
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
}
