"use client";

import React, { useState, useRef, useEffect } from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

/* ──────────────────────────────────────────────────────────────
 *  Subtle info icon + tooltip for explaining AI metrics/features.
 *  Appears on hover or focus — keeps out of the way otherwise.
 * ────────────────────────────────────────────────────────────── */

interface ExplainabilityTooltipProps {
  /** Short explanation shown in the tooltip bubble */
  content: string;
  /** Optional longer description below the main content */
  detail?: string;
  /** Size of the info icon in px */
  size?: number;
  /** Additional className for the icon wrapper */
  className?: string;
  /** Position preference */
  position?: "top" | "bottom" | "left" | "right";
}

export function ExplainabilityTooltip({
  content,
  detail,
  size = 13,
  className,
  position = "top",
}: ExplainabilityTooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const show = () => {
    clearTimeout(timeoutRef.current);
    setVisible(true);
  };
  const hide = () => {
    timeoutRef.current = setTimeout(() => setVisible(false), 150);
  };

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  const arrowClasses = {
    top: "top-full left-1/2 -translate-x-1/2 border-t-gray-900 dark:border-t-gray-700 border-x-transparent border-b-transparent",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-gray-900 dark:border-b-gray-700 border-x-transparent border-t-transparent",
    left: "left-full top-1/2 -translate-y-1/2 border-l-gray-900 dark:border-l-gray-700 border-y-transparent border-r-transparent",
    right: "right-full top-1/2 -translate-y-1/2 border-r-gray-900 dark:border-r-gray-700 border-y-transparent border-l-transparent",
  };

  return (
    <span
      className={cn("relative inline-flex items-center", className)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <button
        type="button"
        className="p-0.5 rounded-full text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-500"
        aria-label="More information"
        tabIndex={0}
      >
        <Info size={size} />
      </button>

      {visible && (
        <div
          className={cn(
            "absolute z-50 w-56 px-3 py-2 rounded-lg shadow-lg",
            "bg-gray-900 dark:bg-gray-700 text-white",
            "text-[11px] leading-relaxed",
            "pointer-events-none animate-in fade-in-0 zoom-in-95 duration-150",
            positionClasses[position],
          )}
          role="tooltip"
        >
          <p className="font-medium">{content}</p>
          {detail && (
            <p className="mt-1 text-gray-300 dark:text-gray-400 text-[10px]">{detail}</p>
          )}
          {/* Arrow */}
          <span
            className={cn(
              "absolute w-0 h-0 border-4",
              arrowClasses[position],
            )}
            aria-hidden="true"
          />
        </div>
      )}
    </span>
  );
}
