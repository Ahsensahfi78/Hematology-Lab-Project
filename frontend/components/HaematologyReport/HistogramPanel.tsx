"use client";

import { useEffect, useRef } from "react";
import draw from "./draw";

// A single canvas histogram with axis ticks + a curve drawn from a shape fn.
// Redraws on every render where the dependent param values change.

export interface HistogramShape {
  /** color of the curve stroke */
  color: string;
  /** axis tick positions (0..1 across width) + labels */
  ticks: { pos: number; label: string }[];
  /** fn(x) with x in [0,1], returns a height 0..1 */
  fn: (x: number) => number;
}

interface Props {
  title: string;
  shape: HistogramShape;
  /** optional ref callback so a parent can reach the underlying <canvas> */
  canvasRefOverride?: (el: HTMLCanvasElement | null) => void;
}

export default function HistogramPanel({ title, shape, canvasRefOverride }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  // Redraw whenever shape (and therefore dependent params) changes.
  useEffect(() => {
    draw(ref.current, shape, window.devicePixelRatio || 1);
  }, [shape]);

  // Wire the ref callback after mount so the parent can snapshot for print.
  useEffect(() => {
    canvasRefOverride?.(ref.current);
    // call again after redraw so the canvas is always current
    return () => canvasRefOverride?.(null);
  }, [canvasRefOverride, shape]);

  return (
    <div className="rounded border border-slate-200 bg-slate-50/60 px-2.5 py-2 print:break-inside-avoid">
      <h4 className="mb-1 ml-0.5 text-[11.5px] font-medium tracking-wide text-blue-900">
        {title} Histogram
      </h4>
      <canvas
        ref={ref}
        onClick={(e) => {
          const el = e.currentTarget;
          draw(el, shape, window.devicePixelRatio || 1);
        }}
        width={280}
        height={110}
        className="block h-[110px] w-full"
      />
    </div>
  );
}