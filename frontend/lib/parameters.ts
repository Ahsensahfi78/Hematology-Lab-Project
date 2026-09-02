import type { ParameterMeta } from "./types";

export type PanelType = "LMG" | "NEU";

// (key, label, unit, group, description)
const RAW: [string, string, string, string, string][] = [
  // WBC
  ["wbc", "WBC (White Blood Cell Count)", "x10^3/uL", "wbc", "Total number of white blood cells, which fight infection."],
  ["lymph_pct", "Lymphocytes (%)", "%", "wbc", "Lymphocytes as a % of white cells (immune cells)."],
  ["mid_pct", "Mid Cells (%)", "%", "wbc", "Mid-sized cells (monocytes, eosinophils, basophils) as a %."],
  ["gran_pct", "Granulocytes (%)", "%", "wbc", "Granulocytes (neutrophils and others) as a % of white cells."],
  ["lymph_abs", "Lymphocytes (Absolute)", "/uL", "wbc", "Absolute number of lymphocytes."],
  ["mid_abs", "Mid Cells (Absolute)", "/uL", "wbc", "Absolute number of mid-sized cells."],
  ["gran_abs", "Granulocytes (Absolute)", "/uL", "wbc", "Absolute number of granulocytes."],
  ["neu_pct", "Neutrophils (%)", "%", "wbc", "Neutrophils (main bacteria-fighting cells) as a %."],
  ["mono_pct", "Monocytes (%)", "%", "wbc", "Monocytes (scavenger cells) as a %."],
  ["eoso_pct", "Eosinophils (%)", "%", "wbc", "Eosinophils (allergy/parasite cells) as a %."],
  ["baso_pct", "Basophils (%)", "%", "wbc", "Basophils as a % (smallest share of white cells)."],
  // RBC
  ["rbc", "RBC (Red Blood Cell Count)", "M/uL", "rbc", "Red blood cells that carry oxygen around the body."],
  ["hgb", "HGB (Haemoglobin)", "g/dL", "rbc", "The oxygen-carrying protein inside red blood cells."],
  ["hct", "HCT (Haematocrit)", "%", "rbc", "The % of your blood made up of red blood cells."],
  ["mcv", "MCV (Mean Corpuscular Volume)", "fL", "rbc", "Average size of a red blood cell."],
  ["mch", "MCH (Mean Corpuscular Hb)", "pg", "rbc", "Average amount of haemoglobin in a single red blood cell."],
  ["mchc", "MCHC (Mean Corpuscular Hb Conc.)", "g/dL", "rbc", "Average concentration of haemoglobin in red blood cells."],
  ["rdw_cv", "RDW-CV", "%", "rbc", "How much red blood cells vary in size (CV method)."],
  ["rdw_sd", "RDW-SD", "fL", "rbc", "How much red blood cells vary in size (SD method)."],
  // PLT
  ["plt", "PLT (Platelet Count)", "x10^3/uL", "plt", "Platelets, which help blood to clot."],
  ["mpv", "MPV (Mean Platelet Volume)", "fL", "plt", "Average size of platelets."],
  ["pdw", "PDW (Platelet Distribution Width)", "%", "plt", "How much platelets vary in size."],
  ["pct", "PCT (Platelet Crit)", "%", "plt", "The % of blood volume made up of platelets."],
];

export const PARAMETERS: ParameterMeta[] = RAW.map(
  ([key, label, unit, group, description]) => ({
    key,
    label,
    unit,
    group,
    description,
  })
);

const BY_KEY: Record<string, ParameterMeta> = Object.fromEntries(
  PARAMETERS.map((p) => [p.key, p])
);

export const GROUP_LABELS: Record<string, string> = {
  wbc: "White Blood Cell (WBC) Panel",
  rbc: "Red Blood Cell (RBC) Panel",
  plt: "Platelet (PLT) Panel",
};

export function getParam(key: string): ParameterMeta {
  return BY_KEY[key] ?? { key, label: key, unit: "", group: "other", description: "" };
}

export const AUTO_CALC: Record<
  string,
  { formula: (r: Record<string, number | null>) => number | null; desc: string }
> = {
  hct: {
    desc: "HCT ≈ RBC × MCV",
    formula: (r) => (num(r.rbc) && num(r.mcv) ? r.rbc! * r.mcv! : null),
  },
  mch: {
    desc: "MCH ≈ HGB ÷ RBC × 10",
    formula: (r) => (num(r.hgb) && num(r.rbc) ? (r.hgb! / r.rbc!) * 10 : null),
  },
  mchc: {
    desc: "MCHC ≈ HGB ÷ HCT × 100",
    formula: (r) => (num(r.hgb) && num(r.hct) ? (r.hgb! / r.hct!) * 100 : null),
  },
};

function num(v: number | null | undefined): v is number {
  return typeof v === "number" && !Number.isNaN(v);
}

export function computeFlag(value: number | null, low: number | null, high: number | null): "H" | "L" | "normal" {
  if (value === null || low === null || high === null) return "normal";
  if (value > high) return "H";
  if (value < low) return "L";
  return "normal";
}

// Default adult reference ranges (low, high)
export const ADULT_REFS: Record<string, { male: [number, number]; female: [number, number] }> = {
  wbc: { male: [4.0, 11.0], female: [4.0, 11.0] },
  lymph_pct: { male: [20.0, 45.0], female: [20.0, 45.0] },
  mid_pct: { male: [3.0, 12.0], female: [3.0, 12.0] },
  gran_pct: { male: [45.0, 70.0], female: [45.0, 70.0] },
  lymph_abs: { male: [1000.0, 4800.0], female: [1000.0, 4800.0] },
  mid_abs: { male: [200.0, 1200.0], female: [200.0, 1200.0] },
  gran_abs: { male: [2500.0, 7000.0], female: [2500.0, 7000.0] },
  neu_pct: { male: [40.0, 75.0], female: [40.0, 75.0] },
  mono_pct: { male: [2.0, 10.0], female: [2.0, 10.0] },
  eoso_pct: { male: [1.0, 6.0], female: [1.0, 6.0] },
  baso_pct: { male: [0.0, 2.0], female: [0.0, 2.0] },
  rbc: { male: [4.5, 5.9], female: [4.0, 5.2] },
  hgb: { male: [13.5, 18.0], female: [12.0, 16.0] },
  hct: { male: [40.0, 54.0], female: [36.0, 48.0] },
  mcv: { male: [80.0, 100.0], female: [80.0, 100.0] },
  mch: { male: [27.0, 33.0], female: [27.0, 33.0] },
  mchc: { male: [32.0, 36.0], female: [32.0, 36.0] },
  rdw_cv: { male: [11.5, 14.5], female: [11.5, 14.5] },
  rdw_sd: { male: [37.0, 54.0], female: [37.0, 54.0] },
  plt: { male: [150.0, 450.0], female: [150.0, 450.0] },
  mpv: { male: [7.4, 10.4], female: [7.4, 10.4] },
  pdw: { male: [9.0, 17.0], female: [9.0, 17.0] },
  pct: { male: [0.15, 0.4], female: [0.15, 0.4] },
};

// Pediatric ranges for age < 14 (override a subset)
const PEDIATRIC_REFS: Record<string, [number, number]> = {
  wbc: [5.0, 13.0],
  rbc: [3.9, 5.5],
  hgb: [11.0, 15.0],
  hct: [33.0, 44.0],
  mcv: [78.0, 98.0],
  mch: [25.0, 33.0],
  mchc: [31.0, 36.0],
};

export function defaultRangeForKey(key: string, age: number, gender: "Male" | "Female"): [number | null, number | null] {
  if (age < 14 && PEDIATRIC_REFS[key]) return PEDIATRIC_REFS[key];
  const adult = ADULT_REFS[key];
  if (!adult) return [null, null];
  return adult[gender === "Male" ? "male" : "female"];
}

export const WBC_DIFF_LMG = ["lymph_pct", "mid_pct", "gran_pct", "lymph_abs", "mid_abs", "gran_abs"];
export const WBC_DIFF_NEU = ["neu_pct", "mono_pct", "eoso_pct", "baso_pct"];

export function visibleKeys(panel: PanelType): string[] {
  const excluded = panel === "NEU" ? ["lymph_abs", "mid_pct", "gran_pct", "mid_abs", "gran_abs"] : WBC_DIFF_NEU;
  return PARAMETERS.filter((p) => !excluded.includes(p.key)).map((p) => p.key);
}
