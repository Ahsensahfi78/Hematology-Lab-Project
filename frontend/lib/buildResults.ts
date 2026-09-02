import type { ResultItem } from "@/lib/types";
import {
  AUTO_CALC,
  computeFlag,
  defaultRangeForKey,
  getParam,
  visibleKeys,
} from "@/lib/parameters";
import type { PanelType } from "@/lib/parameters";

export function buildResults(
  panel: PanelType,
  age: number,
  gender: "Male" | "Female"
): ResultItem[] {
  return visibleKeys(panel).map((key) => {
    const meta = getParam(key);
    const [low, high] = defaultRangeForKey(key, age, gender);
    return {
      parameter_name: key,
      result_value: null,
      unit: meta.unit,
      ref_range_low: low,
      ref_range_high: high,
      flag: "normal",
    };
  });
}

// Rebuild results when panel changes, keeping existing values for shared keys.
export function rebuildForPanel(
  panel: PanelType,
  age: number,
  gender: "Male" | "Female",
  current: ResultItem[]
): ResultItem[] {
  const existing = Object.fromEntries(
    current.map((r) => [r.parameter_name, r])
  );
  return visibleKeys(panel).map((key) => {
    const prev = existing[key];
    if (prev) return prev;
    const meta = getParam(key);
    const [low, high] = defaultRangeForKey(key, age, gender);
    return {
      parameter_name: key,
      result_value: null,
      unit: meta.unit,
      ref_range_low: low,
      ref_range_high: high,
      flag: "normal",
    };
  });
}

// Apply auto-calculations (HCT, MCH, MCHC) from source values.
// Derived fields recalc from their sources unless the user manually overrode them.
export function applyAutoCalc(
  results: ResultItem[],
  manualOverride: Set<string>
): ResultItem[] {
  const values: Record<string, number | null> = {};
  for (const r of results) values[r.parameter_name] = r.result_value;

  return results.map((r) => {
    const rule = AUTO_CALC[r.parameter_name];
    if (!rule) {
      r.flag = computeFlag(r.result_value, r.ref_range_low, r.ref_range_high);
      return r;
    }
    if (manualOverride.has(r.parameter_name)) {
      return r;
    }
    const calc = rule.formula(values);
    if (calc !== null) {
      r.result_value = Math.round(calc * 100) / 100;
    }
    r.flag = computeFlag(r.result_value, r.ref_range_low, r.ref_range_high);
    return r;
  });
}
