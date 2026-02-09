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
 *  MedicalImageViewer — Canvas-based heatmap overlay
 *
 *  How it works:
 *  1. Original medical image drawn as BASE layer on a <canvas>
 *  2. Selected condition's GradCAM heatmap (inferno colormap on
 *     black background) drawn ON TOP with:
 *       - globalCompositeOperation = "screen" → black = invisible
 *       - globalAlpha = overlayOpacity / 100  → 0–100 % control
 *  3. Pan (pointer drag), zoom (wheel), rotate via CSS transforms
 *  4. Changing selected condition swaps the heatmap overlay
 *  5. touch-action:none + passive:false wheel → no page scroll
 * ────────────────────────────────────────────────────────────── */

interface ImageViewerProps {
  /** Original uploaded medical image URL (base layer for overlay) */
  originalImageUrl?: string;
  /** Condition scores with per-condition heatmap URLs */
  conditionScores?: ConditionScore[];
  /** Currently selected condition label */
  selectedLabel?: string;
  /** Callback when user selects a label from the viewer */
  onSelectLabel?: (label: string) => void;
  className?: string;
}

export function ImageViewer({
  originalImageUrl,
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
  const panStartRef = useRef({ x: 0, y: 0 });
  const [showOverlay, setShowOverlay] = useState(true);
  const [overlayOpacity, setOverlayOpacity] = useState(55); // 0–100 %
  const [baseLoaded, setBaseLoaded] = useState(false);
  const [heatmapLoaded, setHeatmapLoaded] = useState(false);
  const [canvasDisplaySize, setCanvasDisplaySize] = useState<{
    w: number;
    h: number;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const baseImgRef = useRef<HTMLImageElement | null>(null);
  const heatmapImgRef = useRef<HTMLImageElement | null>(null);

  /* ── Derived ────────────────────────────────────────────── */
  const sorted = conditionScores
    ? [...conditionScores].sort((a, b) => b.probability - a.probability)
    : [];
  const activeLabel = selectedLabel || sorted[0]?.label;
  const activeScore = sorted.find((s) => s.label === activeLabel);
  const heatmapUrl = activeScore?.heatmap_data_uri;

  // Overlay is possible only when we have a real original image AND a heatmap
  const canOverlay = !!originalImageUrl && !!heatmapUrl;

  // Fallback image when no original image uploaded (standalone heatmap view)
  const fallbackImageUrl =
    heatmapUrl || sorted.find((s) => s.heatmap_data_uri)?.heatmap_data_uri;

  /* ── Canvas draw (composites base + heatmap) ────────────── */
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const baseImg = baseImgRef.current;
    if (!baseImg || !baseImg.naturalWidth) return;

    const w = baseImg.naturalWidth;
    const h = baseImg.naturalHeight;
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // --- Layer 1: original medical image at full opacity ---
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    ctx.drawImage(baseImg, 0, 0, w, h);

    // --- Layer 2: heatmap with screen blend ---
    // "screen" makes black → transparent, warm colors → visible
    const hm = heatmapImgRef.current;
    if (showOverlay && hm && hm.naturalWidth) {
      ctx.globalAlpha = overlayOpacity / 100;
      ctx.globalCompositeOperation = "screen";
      ctx.drawImage(hm, 0, 0, w, h);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }
  }, [showOverlay, overlayOpacity]);

  /* ── Load base (original) image ─────────────────────────── */
  useEffect(() => {
    setBaseLoaded(false);
    baseImgRef.current = null;
    setCanvasDisplaySize(null);
    if (!originalImageUrl) return;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      baseImgRef.current = img;
      // Compute CSS display size (fit within 460×460 preserving ratio)
      const MAX = 460;
      const s = Math.min(MAX / img.naturalWidth, MAX / img.naturalHeight, 1);
      setCanvasDisplaySize({
        w: Math.round(img.naturalWidth * s),
        h: Math.round(img.naturalHeight * s),
      });
      setBaseLoaded(true);
    };
    img.onerror = () => setBaseLoaded(false);
    img.src = originalImageUrl;
  }, [originalImageUrl]);

  /* ── Load heatmap (swapped when condition changes) ──────── */
  useEffect(() => {
    setHeatmapLoaded(false);
    heatmapImgRef.current = null;
    if (!heatmapUrl) return;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      heatmapImgRef.current = img;
      setHeatmapLoaded(true);
    };
    img.src = heatmapUrl;
  }, [heatmapUrl]);

  /* ── Redraw canvas on any visual change ─────────────────── */
  useEffect(() => {
    if (baseLoaded) draw();
  }, [baseLoaded, heatmapLoaded, showOverlay, overlayOpacity, draw]);

  /* ── Pointer (unified mouse + touch) pan ────────────────── */
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return;
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [pan],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isPanning) return;
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
    },
    [isPanning],
  );

  const handlePointerUp = useCallback(() => setIsPanning(false), []);

  /* ── Wheel zoom — { passive: false } blocks page scroll ── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom((z) => Math.max(0.25, Math.min(5, z + delta)));
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, []);

  /* ── Keyboard shortcuts ─────────────────────────────────── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "+" || e.key === "=")
        setZoom((z) => Math.min(z + 0.25, 5));
      else if (e.key === "-" || e.key === "_")
        setZoom((z) => Math.max(z - 0.25, 0.25));
      else if (e.key === "r") setRotation((r) => r + 90);
      else if (e.key === "0") {
        setZoom(1);
        setRotation(0);
        setPan({ x: 0, y: 0 });
      }
    };
    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, []);

  const resetView = () => {
    setZoom(1);
    setRotation(0);
    setPan({ x: 0, y: 0 });
  };

  /* ── CSS transform for pan / zoom / rotate ──────────────── */
  const transformStyle: React.CSSProperties = {
    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom}) rotate(${rotation}deg)`,
    transition: isPanning ? "none" : "transform 0.2s ease-out",
    transformOrigin: "center center",
  };

  /* ── Render mode ────────────────────────────────────────── */
  const useCanvasMode = !!originalImageUrl;

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
            detail="Heatmaps show where the MedSigLIP vision model focuses when evaluating each condition. Warmer colors = higher attention. The heatmap is composited onto the original image using screen blending."
            size={11}
            position="bottom"
          />
        </div>
        <div className="flex items-center gap-1">
          {/* Heatmap overlay toggle — only when overlay is possible */}
          {canOverlay && (
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
              Overlay {showOverlay ? "On" : "Off"}
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

      {/* ── Heatmap opacity slider (0 – 100 %) ──────── */}
      {canOverlay && showOverlay && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 border-b border-gray-800">
          <span className="text-[10px] text-gray-500 w-14">Opacity</span>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseInt(e.target.value, 10))}
            className="flex-1 h-1 accent-accent-rose"
            aria-label="Heatmap overlay opacity"
          />
          <span className="text-[10px] text-gray-500 w-8 text-right">
            {overlayOpacity}%
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

      {/* ── Image viewport (touch-action:none blocks page scroll) */}
      <div
        ref={containerRef}
        className={cn(
          "relative flex items-center justify-center overflow-hidden bg-gray-950 min-h-[420px]",
          isPanning ? "cursor-grabbing" : "cursor-grab",
        )}
        style={{ touchAction: "none" }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        tabIndex={0}
        role="img"
        aria-label={`Medical image viewer${activeLabel ? ` — showing ${activeLabel} attention map` : ""}`}
      >
        {useCanvasMode && baseLoaded ? (
          /* ── Canvas compositing: base image + heatmap overlay ── */
          <canvas
            ref={canvasRef}
            className="select-none rounded-lg"
            style={{
              ...transformStyle,
              width: canvasDisplaySize?.w ?? 460,
              height: canvasDisplaySize?.h ?? 460,
            }}
            draggable={false}
          />
        ) : useCanvasMode && !baseLoaded ? (
          /* ── Loading spinner ── */
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : fallbackImageUrl ? (
          /* ── Fallback: no original → show heatmap directly ── */
          <img
            src={heatmapUrl || fallbackImageUrl}
            alt={`Attention heatmap for ${activeLabel || "condition"}`}
            className="max-w-[460px] max-h-[460px] rounded-lg object-contain select-none"
            style={transformStyle}
            draggable={false}
          />
        ) : (
          /* ── No image at all ── */
          <div className="text-center text-gray-500 py-12">
            <div className="text-5xl mb-3">📷</div>
            <p className="text-sm">No medical image available</p>
            <p className="text-xs text-gray-600 mt-1">
              Image explainability data will appear here
            </p>
          </div>
        )}

        {/* Pan hint */}
        {(useCanvasMode || fallbackImageUrl) && (
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
