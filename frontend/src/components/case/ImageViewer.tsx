"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";
import { ExplainabilityTooltip } from "@/components/shared/ExplainabilityTooltip";
import type { ConditionScore } from "@/lib/types";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RotateCw,
  Maximize2,
  Layers,
  Move,
} from "lucide-react";

/* ──────────────────────────────────────────────────────────────
 *  MedicalImageViewer — ImageViewer rewrite
 *
 *  Features:
 *  • Displays the actual medical image (base64 or URL)
 *  • Overlays per-condition GradCAM heatmaps with opacity control
 *  • Pan (mouse drag), zoom (wheel + buttons), rotate (90° steps)
 *  • Condition selector synced with ConditionScoresChart
 * ────────────────────────────────────────────────────────────── */

interface ImageViewerProps {
  /** Primary image URL (attention_heatmap_url or first heatmap) */
  imageUrl?: string;
  /** Condition scores with per-condition heatmap URLs */
  conditionScores?: ConditionScore[];
  /** Currently selected condition label */
  selectedLabel?: string;
  /** Callback when user selects a label from the viewer */
  onSelectLabel?: (label: string) => void;
  className?: string;
}

export function ImageViewer({
  imageUrl,
  conditionScores,
  selectedLabel,
  onSelectLabel,
  className,
}: ImageViewerProps) {
  /* ── State ──────────────────────────────────────────────── */
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [showOverlay, setShowOverlay] = useState(true);
  const [overlayOpacity, setOverlayOpacity] = useState(0.55);
  const [imgLoaded, setImgLoaded] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  /* ── Derived ────────────────────────────────────────────── */
  const sorted = conditionScores
    ? [...conditionScores].sort((a, b) => b.probability - a.probability)
    : [];
  const activeLabel = selectedLabel || sorted[0]?.label;
  const activeScore = sorted.find((s) => s.label === activeLabel);
  const heatmapUrl = activeScore?.heatmap_data_uri;

  // Base image: the top attention heatmap or first available image
  const baseImageUrl =
    imageUrl || sorted.find((s) => s.heatmap_data_uri)?.heatmap_data_uri;

  /* ── Pan handlers ───────────────────────────────────────── */
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    },
    [pan],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isPanning) return;
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    },
    [isPanning, panStart],
  );

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  /* ── Zoom with wheel ────────────────────────────────────── */
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => {
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      return Math.max(0.25, Math.min(5, z + delta));
    });
  }, []);

  /* ── Reset view ─────────────────────────────────────────── */
  const resetView = () => {
    setZoom(1);
    setRotation(0);
    setPan({ x: 0, y: 0 });
  };

  /* ── Touch support for mobile ───────────────────────────── */
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length !== 1) return;
      const t = e.touches[0];
      setIsPanning(true);
      setPanStart({ x: t.clientX - pan.x, y: t.clientY - pan.y });
    },
    [pan],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isPanning || e.touches.length !== 1) return;
      const t = e.touches[0];
      setPan({
        x: t.clientX - panStart.x,
        y: t.clientY - panStart.y,
      });
    },
    [isPanning, panStart],
  );

  const handleTouchEnd = useCallback(() => setIsPanning(false), []);

  /* ── Keyboard zoom/rotate ───────────────────────────────── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(z + 0.25, 5));
      else if (e.key === "-" || e.key === "_") setZoom((z) => Math.max(z - 0.25, 0.25));
      else if (e.key === "r") setRotation((r) => r + 90);
      else if (e.key === "0") resetView();
    };
    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, []);

  /* ── Render ─────────────────────────────────────────────── */
  const transformStyle = {
    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom}) rotate(${rotation}deg)`,
    transition: isPanning ? "none" : "transform 0.2s ease-out",
  };

  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-black",
        className,
      )}
    >
      {/* ── Toolbar ──────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-400">
            Medical Image Viewer
          </span>
          <ExplainabilityTooltip
            content="GradCAM attention visualization"
            detail="Heatmaps show where the MedSigLIP vision model focuses when evaluating each condition. Warmer colors = higher attention."
            size={11}
            position="bottom"
          />
        </div>
        <div className="flex items-center gap-1">
          {/* Heatmap overlay toggle */}
          {heatmapUrl && (
            <button
              onClick={() => setShowOverlay((v) => !v)}
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition",
                showOverlay
                  ? "bg-accent-rose/20 text-accent-rose"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200",
              )}
              aria-pressed={showOverlay}
              aria-label="Toggle heatmap overlay"
            >
              <Layers size={12} />
              Overlay
            </button>
          )}

          <div className="w-px h-4 bg-gray-700 mx-1" aria-hidden="true" />

          {/* Zoom controls */}
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.25, 5))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Zoom in"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.25, 0.25))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Zoom out"
          >
            <ZoomOut size={14} />
          </button>

          <div className="w-px h-4 bg-gray-700 mx-0.5" aria-hidden="true" />

          {/* Rotate controls */}
          <button
            onClick={() => setRotation((r) => r - 90)}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Rotate counter-clockwise"
          >
            <RotateCcw size={14} />
          </button>
          <button
            onClick={() => setRotation((r) => r + 90)}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Rotate clockwise"
          >
            <RotateCw size={14} />
          </button>

          <div className="w-px h-4 bg-gray-700 mx-0.5" aria-hidden="true" />

          {/* Reset */}
          <button
            onClick={resetView}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Reset view"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* ── Heatmap opacity slider ───────────────────── */}
      {showOverlay && heatmapUrl && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 border-b border-gray-800">
          <span className="text-[10px] text-gray-500 w-14">Opacity</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
            className="flex-1 h-1 accent-accent-rose"
            aria-label="Heatmap overlay opacity"
          />
          <span className="text-[10px] text-gray-500 w-8 text-right">
            {Math.round(overlayOpacity * 100)}%
          </span>
        </div>
      )}

      {/* ── Condition label tabs ─────────────────────── */}
      {sorted.length > 0 && (
        <div className="flex items-center gap-1 px-3 py-1.5 bg-gray-900/60 border-b border-gray-800 overflow-x-auto scrollbar-thin">
          {sorted.slice(0, 8).map((score) => (
            <button
              key={score.label}
              onClick={() => onSelectLabel?.(score.label)}
              className={cn(
                "flex-shrink-0 px-2 py-0.5 rounded-md text-[10px] font-medium transition whitespace-nowrap",
                activeLabel === score.label
                  ? "bg-brand-500/20 text-brand-400 ring-1 ring-brand-500/30"
                  : "bg-gray-800 text-gray-500 hover:text-gray-300",
              )}
            >
              {score.label}
              <span className="ml-1 opacity-60">
                {(score.probability * 100).toFixed(0)}%
              </span>
            </button>
          ))}
        </div>
      )}

      {/* ── Image viewport ───────────────────────────── */}
      <div
        ref={containerRef}
        className={cn(
          "relative flex items-center justify-center overflow-hidden bg-gray-950 min-h-[420px]",
          isPanning ? "cursor-grabbing" : "cursor-grab",
        )}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        tabIndex={0}
        role="img"
        aria-label={`Medical image viewer${activeLabel ? ` — showing ${activeLabel} attention map` : ""}`}
      >
        {baseImageUrl ? (
          <div className="relative" style={transformStyle}>
            {/* Base medical image */}
            <img
              src={baseImageUrl}
              alt="Medical image — AI analysis"
              className={cn(
                "max-w-[460px] max-h-[460px] rounded-lg object-contain select-none",
                imgLoaded ? "opacity-100" : "opacity-0",
              )}
              onLoad={() => setImgLoaded(true)}
              draggable={false}
            />

            {/* Heatmap overlay */}
            {showOverlay && heatmapUrl && heatmapUrl !== baseImageUrl && (
              <img
                src={heatmapUrl}
                alt={`Attention heatmap for ${activeLabel}`}
                className="absolute inset-0 w-full h-full rounded-lg object-contain select-none pointer-events-none"
                style={{ opacity: overlayOpacity, mixBlendMode: "screen" }}
                draggable={false}
              />
            )}

            {/* Loading placeholder */}
            {!imgLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-12">
            <div className="text-5xl mb-3">📷</div>
            <p className="text-sm">No medical image available</p>
            <p className="text-xs text-gray-600 mt-1">
              Image explainability data will appear here
            </p>
          </div>
        )}

        {/* Pan hint */}
        {baseImageUrl && (
          <div className="absolute bottom-2 left-2 flex items-center gap-1 px-2 py-1 rounded-md bg-black/60 text-gray-400 text-[9px] pointer-events-none">
            <Move size={10} />
            Drag to pan · Scroll to zoom · R to rotate
          </div>
        )}

        {/* Zoom indicator */}
        {zoom !== 1 && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-md bg-black/60 text-gray-300 text-[10px] font-mono pointer-events-none">
            {(zoom * 100).toFixed(0)}%
          </div>
        )}
      </div>

      {/* ── Active condition badge ────────────────────── */}
      {activeLabel && (
        <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-t border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
            <span className="text-xs font-medium text-gray-300">
              Viewing: <span className="text-white">{activeLabel}</span>
            </span>
          </div>
          {activeScore && (
            <span
              className={cn(
                "text-xs font-mono font-semibold",
                activeScore.probability >= 0.3
                  ? "text-rose-400"
                  : "text-gray-400",
              )}
            >
              {(activeScore.probability * 100).toFixed(1)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}
