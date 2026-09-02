"use client";

import type { ResultItem } from "@/lib/types";
import { GROUP_LABELS, getParam, visibleKeys } from "@/lib/parameters";
import type { PanelType } from "@/lib/parameters";
import ResultRow from "./ResultRow";

interface Props {
  results: ResultItem[];
  panel: PanelType;
  onPanelChange: (p: PanelType) => void;
  onResultChange: (key: string, updates: Partial<ResultItem>) => void;
}

const GROUP_ORDER = ["wbc", "rbc", "plt"];

export default function ResultEditor({
  results,
  panel,
  onPanelChange,
  onResultChange,
}: Props) {
  const byKey: Record<string, ResultItem> = Object.fromEntries(
    results.map((r) => [r.parameter_name, r])
  );

  const handlePanel = (p: PanelType) => {
    onPanelChange(p);
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700">
          WBC differential panel:
        </span>
        <label className="flex items-center gap-1.5 text-sm">
          <input
            type="radio"
            checked={panel === "LMG"}
            onChange={() => handlePanel("LMG")}
            className="accent-blue-600"
          />
          Lymph / Mid / Gran
        </label>
        <label className="flex items-center gap-1.5 text-sm">
          <input
            type="radio"
            checked={panel === "NEU"}
            onChange={() => handlePanel("NEU")}
            className="accent-blue-600"
          />
          Neu / Lymph / Mono / Eoso / Baso
        </label>
      </div>

      {GROUP_ORDER.map((group) => {
        const keys = visibleKeys(panel).filter(
          (k) => getParam(k).group === group
        );
        if (keys.length === 0) return null;
        return (
          <div
            key={group}
            className="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
          >
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
              <h3 className="text-sm font-semibold text-slate-700">
                {GROUP_LABELS[group]}
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="bg-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Parameter</th>
                    <th className="px-3 py-2">Result</th>
                    <th className="px-3 py-2">Unit</th>
                    <th className="px-3 py-2">Reference Range</th>
                    <th className="px-3 py-2 text-center">Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => {
                    const item = byKey[key];
                    if (!item) return null;
                    const meta = getParam(key);
                    return (
                      <ResultRow
                        key={key}
                        label={meta.label}
                        description={meta.description}
                        value={item}
                        onChange={(u) => onResultChange(key, u)}
                      />
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
