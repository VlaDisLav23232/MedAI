"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

interface ImageViewerProps {
  imageUrl?: string;
  heatmapUrl?: string;
  findings?: { finding: string; region_bbox?: [number, number, number, number]; confidence: number }[];
  className?: string;
}

export function ImageViewer({
  imageUrl,
  heatmapUrl,
  findings,
  className,
}: ImageViewerProps) {
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showRegions, setShowRegions] = useState(true);
  const [zoom, setZoom] = useState(1);

  return (
    <div className={cn("flex flex-col rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-black", className)}>
      {/* Image toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
        <span className="text-xs font-medium text-gray-400">
          Medical Image Viewer
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition",
              showHeatmap
                ? "bg-accent-rose/20 text-accent-rose"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            )}
          >
            {showHeatmap ? <EyeOff size={12} /> : <Eye size={12} />}
            Heatmap
          </button>
          <button
            onClick={() => setShowRegions(!showRegions)}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition",
              showRegions
                ? "bg-accent-cyan/20 text-accent-cyan"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            )}
          >
            Regions
          </button>
          <div className="w-px h-4 bg-gray-700 mx-1" />
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Image area */}
      <div className="relative flex items-center justify-center overflow-hidden bg-gray-950 min-h-[400px]">
        {imageUrl ? (
          <div
            className="relative transition-transform duration-200"
            style={{ transform: `scale(${zoom})` }}
          >
            {/* Placeholder for actual image */}
            <div className="w-[400px] h-[400px] bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-2">🩻</div>
                <span className="text-sm text-gray-500">CXR Image</span>
                <p className="text-xs text-gray-600 mt-1">cxr-20260207.dcm</p>
              </div>
            </div>

            {/* Heatmap overlay */}
            {showHeatmap && (
              <div className="absolute inset-0 rounded-lg overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-red-500/0 via-yellow-500/0 to-red-500/0" />
                {/* Simulated heatmap region */}
                <div
                  className="absolute bg-gradient-radial from-red-500/40 via-yellow-400/25 to-transparent rounded-full blur-xl animate-pulse-slow"
                  style={{
                    left: "55%",
                    top: "60%",
                    width: "160px",
                    height: "140px",
                    transform: "translate(-50%, -50%)",
                  }}
                />
                <div
                  className="absolute bg-gradient-radial from-orange-500/30 to-transparent rounded-full blur-lg"
                  style={{
                    left: "58%",
                    top: "63%",
                    width: "100px",
                    height: "90px",
                    transform: "translate(-50%, -50%)",
                  }}
                />
              </div>
            )}

            {/* Region bounding boxes */}
            {showRegions &&
              findings?.map((f, i) =>
                f.region_bbox ? (
                  <div
                    key={i}
                    className="absolute border-2 border-accent-cyan/70 rounded-lg group cursor-pointer"
                    style={{
                      left: `${(f.region_bbox[0] / 512) * 100}%`,
                      top: `${(f.region_bbox[1] / 512) * 100}%`,
                      width: `${((f.region_bbox[2] - f.region_bbox[0]) / 512) * 100}%`,
                      height: `${((f.region_bbox[3] - f.region_bbox[1]) / 512) * 100}%`,
                    }}
                  >
                    {/* Label */}
                    <div className="absolute -top-6 left-0 px-2 py-0.5 bg-accent-cyan text-white text-[10px] font-semibold rounded whitespace-nowrap">
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
