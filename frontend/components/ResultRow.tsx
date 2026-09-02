"use client";

import { useEffect, useRef, useState } from "react";
import type { ResultItem } from "@/lib/types";
import { computeFlag } from "@/lib/parameters";
import FlagBadge from "./FlagBadge";

interface Props {
  label: string;
  description?: string;
  value: ResultItem;
  onChange: (updates: Partial<ResultItem>) => void;
}

export default function ResultRow({ label, description, value, onChange }: Props) {
  const [showTip, setShowTip] = useState(false);
  const flag = computeFlag(value.result_value, value.ref_range_low, value.ref_range_high);
  const rowRef = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    const flag = computeFlag(value.result_value, value.ref_range_low, value.ref_range_high);
    if (flag !== value.flag) {
      onChange({ flag });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value.result_value, value.ref_range_low, value.ref_range_high]);

  return (
    <tr
      ref={rowRef}
      className={`border-b border-slate-100 transition-colors ${
        flag === "H"
          ? "bg-red-50/60"
          : flag === "L"
          ? "bg-blue-50/60"
          : "hover:bg-slate-50"
      }`}
    >
      <td className="px-3 py-2 align-middle">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-slate-800">{label}</span>
          {description && (
            <button
              type="button"
              className="no-print flex h-4 w-4 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-600 hover:bg-slate-300"
              onClick={() => setShowTip((s) => !s)}
              aria-label={`Info about ${label}`}
              title="Click for explanation"
            >
              ?
            </button>
          )}
        </div>
        {showTip && description && (
          <div className="mt-1 rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
            {description}
          </div>
        )}
      </td>

      <td className="px-3 py-2">
        <input
          type="number"
          step="any"
          value={value.result_value ?? ""}
          onChange={(e) =>
            onChange({
              result_value:
                e.target.value === "" ? null : parseFloat(e.target.value),
            })
          }
          className="w-28 rounded-md border border-slate-300 px-2 py-1.5 text-right text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </td>

      <td className="px-3 py-2">
        <input
          type="text"
          value={value.unit}
          onChange={(e) => onChange({ unit: e.target.value })}
          className="w-24 rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </td>

      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5">
          <input
            type="number"
            step="any"
            value={value.ref_range_low ?? ""}
            onChange={(e) =>
              onChange({
                ref_range_low:
                  e.target.value === "" ? null : parseFloat(e.target.value),
              })
            }
            className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-right text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <span className="text-slate-400">-</span>
          <input
            type="number"
            step="any"
            value={value.ref_range_high ?? ""}
            onChange={(e) =>
              onChange({
                ref_range_high:
                  e.target.value === "" ? null : parseFloat(e.target.value),
              })
            }
            className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-right text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </td>

      <td className="px-3 py-2 text-center">
        <FlagBadge flag={flag} />
      </td>
    </tr>
  );
}
