// Typed configuration for the haematology report parameter table.
// Mirrors the reference HTML (key, label, unit, min, max, defaultValue, section?).

export interface ReportParam {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  defaultValue: number;
  section?: boolean; // insert a visual section break before this row
}

export const REPORT_PARAMS: ReportParam[] = [
  // ---- WBC panel ----
  { key: "WBC", label: "WBC", unit: "10^3/uL", min: 4.0, max: 10.0, defaultValue: 9.0, section: true },
  { key: "NEU", label: "Neu %", unit: "%", min: 50, max: 70, defaultValue: 74 },
  { key: "LYM", label: "Lymp %", unit: "%", min: 20, max: 70, defaultValue: 24 },
  { key: "MONO", label: "Mono %", unit: "%", min: 3, max: 12, defaultValue: 1 },
  { key: "EOS", label: "Eoso %", unit: "%", min: 1, max: 5, defaultValue: 1 },
  { key: "BASO", label: "Baso %", unit: "%", min: 0, max: 1, defaultValue: 0 },
  // ---- RBC panel ----
  { key: "RBC", label: "RBC", unit: "10^6/uL", min: 4.0, max: 5.5, defaultValue: 4.41, section: true },
  { key: "HGB", label: "HGB", unit: "g/dL", min: 12.0, max: 16.0, defaultValue: 13.7 },
  { key: "HCT", label: "HCT", unit: "%", min: 10.0, max: 51.0, defaultValue: 38.5 },
  { key: "MCV", label: "MCV", unit: "fL", min: 80.0, max: 100.0, defaultValue: 87.3 },
  { key: "MCH", label: "MCH", unit: "pg", min: 27.0, max: 34.0, defaultValue: 31.2 },
  { key: "MCHC", label: "MCHC", unit: "g/dL", min: 32.0, max: 36.0, defaultValue: 35.7 },
  { key: "RDWCV", label: "RDW-CV", unit: "%", min: 11.0, max: 16.0, defaultValue: 12.3 },
  { key: "RDWSD", label: "RDW-SD", unit: "fL", min: 35.0, max: 56.0, defaultValue: 36.5 },
  // ---- PLT panel ----
  { key: "PLT", label: "PLT", unit: "10^3/uL", min: 150, max: 450, defaultValue: 146, section: true },
  { key: "MPV", label: "MPV", unit: "fL", min: 6.5, max: 12.0, defaultValue: 9.7 },
  { key: "PDW", label: "PDW", unit: "", min: 15.0, max: 17.0, defaultValue: 16.3 },
  { key: "PCT", label: "PCT", unit: "%", min: 0.108, max: 0.282, defaultValue: 0.142 },
];

// Initial values keyed by param key (from defaultValue) — used to seed state.
export function initialValues(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const p of REPORT_PARAMS) out[p.key] = p.defaultValue;
  return out;
}

// Reference range lookup used for local H/L recompute.
export function rangeFor(paramKey: string): [number, number] | null {
  const p = REPORT_PARAMS.find((x) => x.key === paramKey);
  return p ? [p.min, p.max] : null;
}

// Compute H / L / normal for a value against a min / max.
export type Flag = "H" | "L" | "normal";
export function computeFlag(value: number | null, min: number | null, max: number | null): Flag {
  if (value == null || min == null || max == null) return "normal";
  if (value > max) return "H";
  if (value < min) return "L";
  return "normal";
}

// Mapping from backend canonical keys (parameters.ts) to reportParams keys.
const BACKEND_TO_REPORT: Record<string, string> = {
  wbc: "WBC",
  neu_pct: "NEU",
  lymph_pct: "LYM",
  mono_pct: "MONO",
  eoso_pct: "EOS",
  baso_pct: "BASO",
  rbc: "RBC",
  hgb: "HGB",
  hct: "HCT",
  mcv: "MCV",
  mch: "MCH",
  mchc: "MCHC",
  rdw_cv: "RDWCV",
  rdw_sd: "RDWSD",
  plt: "PLT",
  mpv: "MPV",
  pdw: "PDW",
  pct: "PCT",
  // 3-panel diff aliases
  lymph_abs: "", // not in reportParams — skip
  mid_pct: "",
  mid_abs: "",
  gran_pct: "",
  gran_abs: "",
};

// Convert a backend results array into reportParams-keyed values.
export function backendResultsToReportParams(
  results: { parameter_name: string; result_value: number | null }[]
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of results) {
    const key = BACKEND_TO_REPORT[r.parameter_name];
    if (key && r.result_value != null) out[key] = r.result_value;
  }
  return out;
}