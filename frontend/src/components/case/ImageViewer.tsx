"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw, Crosshair } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FindingRegion {
  finding: string;
  region_bbox?: [number, number, number, number]; // [x1, y1, x2, y2] in px relative to 512×512 grid
  confidence: number;
}

interface ImageViewerProps {
  imageUrl?: string;
  heatmapUrl?: string;
  findings?: FindingRegion[];
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Heatmap color palette                                              */
/* ------------------------------------------------------------------ */

/** Jet-like colormap for a 0-1 intensity value → [r, g, b, a]. */
function heatColor(t: number): [number, number, number, number] {
  // 0-0.25 → blue→cyan, 0.25-0.5 → cyan→green, 0.5-0.75 → green→yellow, 0.75-1 → yellow→red
  const clamped = Math.max(0, Math.min(1, t));
  let r = 0,
    g = 0,
    b = 0;
  if (clamped < 0.25) {
    b = 1;
    g = clamped / 0.25;
  } else if (clamped < 0.5) {
    g = 1;
    b = 1 - (clamped - 0.25) / 0.25;
  } else if (clamped < 0.75) {
    g = 1;
    r = (clamped - 0.5) / 0.25;
  } else {
    r = 1;
    g = 1 - (clamped - 0.75) / 0.25;
  }
  const alpha = clamped * 0.55; // hotter → more opaque
  return [r * 255, g * 255, b * 255, alpha * 255];
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ImageViewer({
  imageUrl,
  heatmapUrl,
  findings,
  className,
}: ImageViewerProps) {
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showRegions, setShowRegions] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fixed logical size of the canvas; matches the placeholder image
  const SIZE = 400;
  // Findings bbox coordinates are relative to a 512×512 grid
  const BBOX_GRID = 512;

  /* ── Draw procedural heatmap from finding bounding boxes ────── */
  const drawProceduralHeatmap = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number) => {
      if (!findings || findings.length === 0) return;

      // Build intensity field
      const intensityBuf = new Float32Array(w * h);

      for (const f of findings) {
        if (!f.region_bbox) continue;
        const [x1Raw, y1Raw, x2Raw, y2Raw] = f.region_bbox;
        // Normalise to canvas pixel space
        const cx = (((x1Raw + x2Raw) / 2) / BBOX_GRID) * w;
        const cy = (((y1Raw + y2Raw) / 2) / BBOX_GRID) * h;
        const radiusX = (((x2Raw - x1Raw) / 2) / BBOX_GRID) * w * 1.3; // extend slightly
        const radiusY = (((y2Raw - y1Raw) / 2) / BBOX_GRID) * h * 1.3;
        const peakIntensity = f.confidence;

        // Gaussian-ish blob
        const rMax = Math.max(radiusX, radiusY) * 1.8;
        const x0 = Math.max(0, Math.floor(cx - rMax));
        const y0 = Math.max(0, Math.floor(cy - rMax));
        const x1 = Math.min(w, Math.ceil(cx + rMax));
        const y1 = Math.min(h, Math.ceil(cy + rMax));

        for (let py = y0; py < y1; py++) {
          for (let px = x0; px < x1; px++) {
            const dx = (px - cx) / radiusX;
            const dy = (py - cy) / radiusY;
            const d2 = dx * dx + dy * dy;
            if (d2 > 4) continue; // beyond 2-sigma
            const val = peakIntensity * Math.exp(-d2 / 2);
            const idx = py * w + px;
            intensityBuf[idx] = Math.min(1, intensityBuf[idx] + val);
          }
        }
      }

      // Convert intensity to RGBA image
      const imgData = ctx.createImageData(w, h);
      for (let i = 0; i < w * h; i++) {
        const [r, g, b, a] = heatColor(intensityBuf[i]);
        imgData.data[i * 4 + 0] = r;
        imgData.data[i * 4 + 1] = g;
        imgData.data[i * 4 + 2] = b;
        imgData.data[i * 4 + 3] = a;
      }
      ctx.putImageData(imgData, 0, 0);
    },
    [findings]
  );

  /* ── Draw heatmap from URL (downloaded image overlay) ──────── */
  const drawImageHeatmap = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number) => {
      if (!heatmapUrl) return;
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0, w, h);
      };
      img.src = heatmapUrl;
    },
    [heatmapUrl]
  );

  /* ── Main render loop ──────────────────────────────────────── */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !showHeatmap) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    if (heatmapUrl) {
      drawImageHeatmap(ctx, w, h);
    } else {
      drawProceduralHeatmap(ctx, w, h);
    }
  }, [showHeatmap, heatmapUrl, drawImageHeatmap, drawProceduralHeatmap]);

  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-black",
        className
      )}
    >
      {/* ── Toolbar ──────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
        <span className="text-xs font-medium text-gray-400">
          Medical Image Viewer
        </span>
        <div className="flex items-center gap-1">
          {/* Heatmap toggle */}
          <button
            onClick={() => setShowHeatmap((v) => !v)}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition",
              showHeatmap
                ? "bg-accent-rose/20 text-accent-rose"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            )}
            aria-pressed={showHeatmap}
            aria-label="Toggle heatmap overlay"
          >
            {showHeatmap ? <EyeOff size={12} /> : <Eye size={12} />}
            Heatmap
          </button>

          {/* Region boxes toggle */}
          <button
            onClick={() => setShowRegions((v) => !v)}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition",
              showRegions
                ? "bg-accent-cyan/20 text-accent-cyan"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            )}
            aria-pressed={showRegions}
            aria-label="Toggle region bounding boxes"
          >
            <Crosshair size={12} />
            Regions
          </button>

          <div className="w-px h-4 bg-gray-700 mx-1" aria-hidden="true" />

          {/* Zoom */}
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Zoom in"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Zoom out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
            aria-label="Reset zoom"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* ── Heatmap opacity slider (only visible when heatmap is on) ── */}
      {showHeatmap && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 border-b border-gray-800">
          <span className="text-[10px] text-gray-500 w-14">Opacity</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={heatmapOpacity}
            onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
            className="flex-1 h-1 accent-accent-rose"
            aria-label="Heatmap overlay opacity"
          />
          <span className="text-[10px] text-gray-500 w-8 text-right">
            {Math.round(heatmapOpacity * 100)}%
          </span>
        </div>
      )}

      {/* ── Image + Canvas area ──────────────────────── */}
      <div
        ref={containerRef}
        className="relative flex items-center justify-center overflow-hidden bg-gray-950 min-h-[400px]"
      >
        {imageUrl ? (
          <div
            className="relative transition-transform duration-200"
            style={{ transform: `scale(${zoom})` }}
          >
            {/* Placeholder for actual DICOM/image */}
            <div
              className="w-[400px] h-[400px] bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center"
              role="img"
              aria-label="Medical image — chest X-ray"
            >
              <div className="text-center">
                <div className="text-4xl mb-2">🩻</div>
                <span className="text-sm text-gray-500">CXR Image</span>
                <p className="text-xs text-gray-600 mt-1">cxr-20260207.dcm</p>
              </div>
            </div>

            {/* ── Canvas heatmap overlay ─────────────── */}
            {showHeatmap && (
              <canvas
                ref={canvasRef}
                width={SIZE}
                height={SIZE}
                className="absolute inset-0 rounded-lg pointer-events-none"
                style={{ opacity: heatmapOpacity }}
                aria-hidden="true"
              />
            )}

            {/* ── Region bounding boxes ──────────────── */}
            {showRegions &&
              findings?.map((f, i) =>
                f.region_bbox ? (
                  <div
                    key={i}
                    className="absolute border-2 border-accent-cyan/70 rounded-lg group cursor-pointer transition-colors hover:border-accent-cyan"
                    style={{
                      left: `${(f.region_bbox[0] / BBOX_GRID) * 100}%`,
                      top: `${(f.region_bbox[1] / BBOX_GRID) * 100}%`,
                      width: `${
                        ((f.region_bbox[2] - f.region_bbox[0]) / BBOX_GRID) *
                        100
                      }%`,
                      height: `${
                        ((f.region_bbox[3] - f.region_bbox[1]) / BBOX_GRID) *
                        100
                      }%`,
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`Region: ${f.finding}, confidence ${Math.round(
                      f.confidence * 100
                    )}%`}
                  >
                    {/* Label tooltip */}
                    <div className="absolute -top-6 left-0 px-2 py-0.5 bg-accent-cyan text-white text-[10px] font-semibold rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                      {f.finding} ({Math.round(f.confidence * 100)}%)
                    </div>
                    {/* Corner markers */}
                    <div className="absolute -top-0.5 -left-0.5 w-2 h-2 border-t-2 border-l-2 border-accent-cyan" />
                    <div className="absolute -top-0.5 -right-0.5 w-2 h-2 border-t-2 border-r-2 border-accent-cyan" />
                    <div className="absolute -bottom-0.5 -left-0.5 w-2 h-2 border-b-2 border-l-2 border-accent-cyan" />
                    <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 border-b-2 border-r-2 border-accent-cyan" />
                  </div>
                ) : null
              )}
          </div>
        ) : (
          <div className="text-center text-gray-500">
            <div className="text-5xl mb-3">📷</div>
            <p className="text-sm">No image loaded</p>
          </div>
        )}
      </div>
    </div>
  );
}
