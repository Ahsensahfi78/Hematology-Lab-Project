"use client";

import { useCallback, useMemo, useRef, useState, useEffect } from "react";
import {
  initialValues,
  rangeFor,
  computeFlag,
  type Flag,
} from "@/lib/reportParams";
import ReportHeader from "./HaematologyReport/ReportHeader";
import PatientInfoForm, {
  type PatientFields,
} from "./HaematologyReport/PatientInfoForm";
import ParameterTable from "./HaematologyReport/ParameterTable";
import HistogramPanel, {
  type HistogramShape,
} from "./HaematologyReport/HistogramPanel";
import SignOff from "./HaematologyReport/SignOff";
import draw from "./HaematologyReport/draw";

// PDF-friendly footer strip.
const FOOTER_STRIP =
  "Fully Automated Computerized Chemistry Analyzer | Bio Chemistry Auto Analyzer | Flame Photometer | Immuno Fluorescence Analyzer";

// Helpers mirroring the reference HTML curve logic.
function gauss(x: number, mu: number, sigma: number) {
  return Math.exp(-((x - mu) * (x - mu)) / (2 * sigma * sigma));
}

interface Props {
  /** Initial patient fields; omit for reference defaults. */
  patient?: Partial<PatientFields>;
  /** Initial parameter values keyed by reportParams keys (WBC, NEU, etc.). */
  params?: Record<string, number>;
  /** Initial comments text from the backend report. */
  comments?: string;
  /** Optional persistence callbacks fired on edit. */
  onPatientChange?: (fields: PatientFields) => void;
  onParamsChange?: (values: Record<string, number>) => void;
}

export default function HaematologyReport({
  patient,
  params,
  comments: commentsProp,
  onPatientChange,
  onParamsChange,
}: Props) {
  // ---- patient state ----
  const [patientFields, setPatientFields] = useState<PatientFields>({
    name: "MJM. MALAS",
    sample: "5",
    gender: "Male",
    pid: "53290",
    age: "26 Years",
    date: "02/09/2026",
    requestedBy: "",
    ...patient,
  });

  // ---- parameter values state ----
  const [values, setValues] = useState<Record<string, number>>({
    ...initialValues(),
    ...params,
  });

  // ---- comments field ----
  const [comments, setComments] = useState(commentsProp ?? "");

  // ---- sync external props into state when the caller passes updated data
  //      (e.g. real analyzer results arriving after the initial render).
  //      We track the last values we adopted so we only apply diffs once. ----
  const lastSynced = useRef<{ patient?: Partial<PatientFields>; params?: Record<string, number> }>({});

  useEffect(() => {
    if (patient && patient !== lastSynced.current.patient) {
      lastSynced.current.patient = patient;
      setPatientFields((prev) => ({ ...prev, ...patient }));
    }
  }, [patient, lastSynced]);

  useEffect(() => {
    if (params && params !== lastSynced.current.params) {
      lastSynced.current.params = params;
      setValues((prev) => ({ ...prev, ...params }));
    }
  }, [params, lastSynced]);

  // ---- H/L flags derived from state (useMemo, never manual DOM classes) ----
  const flags = useMemo<Record<string, Flag>>(() => {
    const out: Record<string, Flag> = {};
    for (const key of Object.keys(initialValues())) {
      const range = rangeFor(key);
      out[key] = computeFlag(
        values[key],
        range ? range[0] : null,
        range ? range[1] : null
      );
    }
    return out;
  }, [values]);

  const handlePatientChange = (next: PatientFields) => {
    setPatientFields(next);
    onPatientChange?.(next);
  };

  const handleParamChange = (key: string, value: number) => {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      onParamsChange?.(next);
      return next;
    });
  };

  // ---- histogram shapes derived from current values ----
  const shapes = useMemo(() => {
    const neu = values["NEU"] ?? 0;
    const lym = values["LYM"] ?? 0;
    const lobe1 = 0.35 + (lym / 100) * 0.5;
    const lobe2 = 0.35 + (neu / 100) * 0.5;

    const mcv = values["MCV"] ?? 0;
    const rbcPos = 0.28 + ((mcv - 80) / 40) * 0.15;

    const plt = values["PLT"] ?? 0;
    const pltAmp = Math.min(1, plt / 300);

    return {
      wbc: {
        color: "#1b3a63",
        ticks: [
          { pos: 0, label: "0" },
          { pos: 0.33, label: "100" },
          { pos: 0.66, label: "200" },
          { pos: 1, label: "300 fL" },
        ],
        fn: (x: number) =>
          Math.max(lobe1 * gauss(x, 0.14, 0.05), lobe2 * gauss(x, 0.42, 0.1)),
      },
      rbc: {
        color: "#b5342b",
        ticks: [
          { pos: 0, label: "0" },
          { pos: 0.33, label: "100" },
          { pos: 0.66, label: "200" },
          { pos: 1, label: "300 fL" },
        ],
        fn: (x: number) => gauss(x, rbcPos, 0.045),
      },
      plt: {
        color: "#2e7d4f",
        ticks: [
          { pos: 0, label: "0" },
          { pos: 0.33, label: "10" },
          { pos: 0.66, label: "20" },
          { pos: 1, label: "30 fL" },
        ],
        fn: (x: number) =>
          pltAmp * gauss(x, 0.12, 0.06) * Math.exp(-x * 1.6) + 0.05,
      },
    };
  }, [values]);

  // ---- print: hold real canvas refs (no getElementById), redraw hi-DPI,
  //       then swap to <img> so graphs reliably appear in the print output ----
  const canvasRefs = useRef<{ wbc?: HTMLCanvasElement; rbc?: HTMLCanvasElement; plt?: HTMLCanvasElement }>({});
  const [printSnapshots, setPrintSnapshots] = useState<{ wbc?: string; rbc?: string; plt?: string }>({});

  const setCanvas =
    (key: "wbc" | "rbc" | "plt"): ((el: HTMLCanvasElement | null) => void) =>
    (el) => {
      if (el) canvasRefs.current[key] = el;
      else delete canvasRefs.current[key];
    };

  const preparePrint = useCallback(() => {
    const grab = (
      key: keyof typeof canvasRefs.current,
      shape: HistogramShape,
      dpr = 2
    ): string | undefined => {
      const c = canvasRefs.current[key];
      if (!c) return undefined;
      // Redraw at higher DPI for crisp print output.
      draw(c, shape, dpr);
      return c.toDataURL("image/png");
    };

    setPrintSnapshots({
      wbc: grab("wbc", shapes.wbc),
      rbc: grab("rbc", shapes.rbc),
      plt: grab("plt", shapes.plt),
    });
    // Let React flush the <img> swap, then print.
    requestAnimationFrame(() => setTimeout(() => window.print(), 0));
  }, [shapes]);

  useEffect(() => {
    // After printing, restore interactive canvases so screen editing resumes.
    if (Object.keys(printSnapshots).length > 0) setPrintSnapshots({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-[1000px]">
      {/* Toolbar (hidden on print) */}
      <div className="no-print mb-3.5 flex justify-end gap-2.5">
        <button
          onClick={preparePrint}
          type="button"
          className="rounded-md border border-blue-900 bg-blue-700 px-4 py-2 text-[13.5px] font-semibold text-white transition-colors hover:bg-blue-800"
        >
          Print report
        </button>
      </div>

      {/* Printable sheet */}
      <div className="report-sheet mx-auto w-full max-w-[1000px] border border-slate-200 bg-white px-7 py-6 shadow-sm print:border-0 print:shadow-none">
        <ReportHeader />

        <div className="border-b border-slate-200 pb-2 text-center text-[15px] font-bold tracking-wide">
          Fully Automated Haematology Analyzer Report
        </div>

        {/* Patient info — compact 2-column grid */}
        <div className="mt-3">
          <PatientInfoForm fields={patientFields} onChange={handlePatientChange} />
        </div>

        {/* Side-by-side: parameter table (left) + stacked histograms (right) */}
        <div className="mt-3 grid grid-cols-[1.5fr_1fr] items-start gap-4">
          {/* Left: parameter table */}
          <div>
            <ParameterTable
              values={values}
              flags={flags}
              onValueChange={handleParamChange}
            />
            {/* Comments */}
            <div className="mt-3 flex flex-col text-[12px]">
              <label className="font-semibold text-slate-800">Comments</label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-sm border border-slate-300 bg-transparent px-2 py-1 text-[12px] text-slate-800 print:hidden"
              />
              {comments && (
                <p className="mt-0.5 text-[11px] italic text-slate-600 print:block hidden">
                  {comments}
                </p>
              )}
            </div>
            {/* Technologist signature */}
            <SignOff />
          </div>

          {/* Right: stacked histogram panels */}
          <div className="sticky top-2.5 flex flex-col gap-3 print:static print:pt-2">
            <CanvasPanel title="WBC" shape={shapes.wbc} snapshot={printSnapshots.wbc} onCanvas={setCanvas("wbc")} />
            <CanvasPanel title="RBC" shape={shapes.rbc} snapshot={printSnapshots.rbc} onCanvas={setCanvas("rbc")} />
            <CanvasPanel title="PLT" shape={shapes.plt} snapshot={printSnapshots.plt} onCanvas={setCanvas("plt")} />
          </div>
        </div>

        {/* Footer strip */}
        <div className="mt-3 border-t border-slate-200 pt-1.5 text-center text-[9px] text-slate-400">
          {FOOTER_STRIP}
        </div>
      </div>
    </div>
  );
}

// Redraw helper (shared by panel and print-snapshot path).

// Canvas-or-image panel: on screen shows interactive canvas; during print
// shows a high-DPI <img> snapshot captured from that canvas.
function CanvasPanel({
  title,
  shape,
  snapshot,
  onCanvas,
}: {
  title: string;
  shape: HistogramShape;
  snapshot?: string;
  onCanvas: (el: HTMLCanvasElement | null) => void;
}) {
  if (snapshot) {
    return (
      <div className="rounded border border-slate-200 bg-slate-50/60 px-2.5 py-2 print:break-inside-avoid">
        <h4 className="mb-1 ml-0.5 text-[11.5px] font-medium tracking-wide text-blue-900">
          {title} Histogram
        </h4>
        <img
          src={snapshot}
          alt={`${title} histogram`}
          className="h-[110px] w-full object-contain"
        />
      </div>
    );
  }
  return <HistogramPanelCanvas title={title} shape={shape} canvasRef={onCanvas} />;
}

// Thin wrapper to pass a ref callback into HistogramPanel.
function HistogramPanelCanvas({
  title,
  shape,
  canvasRef,
}: {
  title: string;
  shape: HistogramShape;
  canvasRef: (el: HTMLCanvasElement | null) => void;
}) {
  return (
    <HistogramPanel
      title={title}
      shape={shape}
      canvasRefOverride={canvasRef}
    />
  );
}