"use client";

import type { HistogramShape } from "./HistogramPanel";

// Draw a histogram onto a canvas, optionally at a higher devicePixelRatio.
// Returns the canvas so it can be snapshotted (toDataURL) for printing.
export default function draw(
  canvas: HTMLCanvasElement | null,
  shape: HistogramShape,
  dpr: number = 1
): HTMLCanvasElement | null {
  if (!canvas) return null;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const w = canvas.width;
  const h = canvas.height;

  // Reset transform, then scale by DPR for crisp output.
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  // Baseline + ticks.
  ctx.strokeStyle = "#c7d0da";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(24, h - 16);
  ctx.lineTo(w - 8, h - 16);
  ctx.stroke();

  ctx.fillStyle = "#7a8894";
  ctx.font = "9px Segoe UI, sans-serif";
  ctx.textAlign = "center";
  for (const t of shape.ticks) {
    const x = 24 + t.pos * (w - 32);
    ctx.beginPath();
    ctx.moveTo(x, h - 16);
    ctx.lineTo(x, h - 12);
    ctx.stroke();
    ctx.fillText(t.label, x, h - 4);
  }

  // Curve.
  ctx.strokeStyle = shape.color;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  const n = 120;
  for (let i = 0; i <= n; i++) {
    const x = i / n;
    const y = shape.fn(x);
    const px = 24 + x * (w - 32);
    const py = h - 18 - y * (h - 34);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  return canvas;
}