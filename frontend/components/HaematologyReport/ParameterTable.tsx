"use client";

import { REPORT_PARAMS, type Flag } from "@/lib/reportParams";

interface Props {
  values: Record<string, number>;
  flags: Record<string, Flag>;
  onValueChange: (key: string, value: number) => void;
}

// A4 parameter table: full width with readable columns. Section parameters
// (WBC, RBC, PLT) get a top border separator for visual grouping.
export default function ParameterTable({ values, flags, onValueChange }: Props) {
  return (
    <table className="w-full border-collapse text-[12.5px]">
      <thead>
        <tr className="border-b-[1.5px] border-blue-900 text-[11px] text-blue-900">
          <th className="py-1 pr-1 text-left font-semibold">Parameter</th>
          <th className="w-3 py-1 text-center font-semibold" />
          <th className="w-16 py-1 text-right font-semibold">Result</th>
          <th className="py-1 pl-1 text-left font-semibold">Unit</th>
          <th className="py-1 pl-2 text-left font-semibold">Ref. range</th>
        </tr>
      </thead>
      <tbody>
        {REPORT_PARAMS.map((p) => {
          const flag = flags[p.key];
          const out = flag === "H" || flag === "L";
          return (
            <tr
              key={p.key}
              className={`border-b border-slate-100 ${
                p.section ? "border-t-2 border-blue-900" : ""
              }`}
            >
              <td className="py-1 pr-1 font-semibold text-slate-800">
                {p.label}
              </td>
              <td className="w-3 py-1 text-center">
                {flag !== "normal" && (
                  <span
                    className={[
                      "font-bold text-[11px]",
                      flag === "H" ? "text-[#b5342b]" : "text-[#a9701c]",
                    ].join(" ")}
                  >
                    {flag}
                  </span>
                )}
              </td>
              <td className="w-16 py-1">
                <input
                  type="number"
                  step="any"
                  value={values[p.key]}
                  onChange={(e) =>
                    onValueChange(p.key, parseFloat(e.target.value) || 0)
                  }
                  className={[
                    "w-full rounded-sm border px-1.5 py-0.5 text-right font-mono text-[12px]",
                    out
                      ? "border-[#b5342b] font-bold text-[#b5342b]"
                      : "border-slate-200 text-slate-800 focus:border-blue-700 focus:outline-none",
                  ].join(" ")}
                />
              </td>
              <td className="py-1 pl-1 whitespace-nowrap text-[11.5px] text-slate-500">
                {p.unit}
              </td>
              <td className="py-1 pl-2 whitespace-nowrap text-[11.5px] text-slate-500">
                {p.min}-{p.max}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Export param list so callers can compute flags from a value map.
export const REPORT_PARAM_KEYS = REPORT_PARAMS.map((p) => p.key);