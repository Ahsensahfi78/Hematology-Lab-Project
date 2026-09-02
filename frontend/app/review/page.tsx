"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Report } from "@/lib/types";
import { getParam, GROUP_LABELS } from "@/lib/parameters";
import Header from "@/components/Header";
import { RequireAuth } from "@/components/Auth";
import { useToast } from "@/components/Toast";
import FlagBadge from "@/components/FlagBadge";

const PARAM_ORDER = [
  "wbc","lymph_pct","mid_pct","gran_pct","lymph_abs","mid_abs","gran_abs",
  "neu_pct","mono_pct","eoso_pct","baso_pct","rbc","hgb","hct","mcv","mch",
  "mchc","rdw_cv","rdw_sd","plt","mpv","pdw","pct",
];

function fmt(s?: string) {
  if (!s) return "-";
  return new Date(s).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function ReviewPage() {
  const { toast } = useToast();
  const [queue, setQueue] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Report | null>(null);
  const [notes, setNotes] = useState("");
  const [reviewedIds, setReviewedIds] = useState<number[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const q = await api.reviewQueue();
      setQueue(q);
    } catch (e: any) {
      toast(e.message || "Failed to load review queue", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const open = async (id: number) => {
    try {
      const r = await api.getReport(id);
      setSelected(r);
      setNotes("");
    } catch (e: any) {
      toast(e.message || "Failed to load report", "error");
    }
  };

  const signOff = async (status: "reviewed" | "revised") => {
    if (!selected) return;
    try {
      const updated = await api.verifyReport(selected.id, status, notes);
      toast("Report released");
      setReviewedIds((xs) => [...xs, selected.id]);
      setSelected(null);
      await load();
    } catch (e: any) {
      toast(e.message || "Sign-off failed", "error");
    }
  };

  // Sort selected results by canonical order
  const order = (r: any) => PARAM_ORDER.indexOf(r.parameter_name) ?? 999;

  const resultsByGroup = (list: Report["results"]) => {
    const g: Record<string, typeof list> = {};
    for (const r of list) {
      const grp = getParam(r.parameter_name).group;
      (g[grp] = g[grp] || []).push(r);
    }
    Object.values(g).forEach((arr) => arr.sort((a, b) => order(a) - order(b)));
    return g;
  };

  const pendingDisplay = queue.filter((r) => !reviewedIds.includes(r.id));

  return (
    <RequireAuth>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Pathologist Review</h1>
            <p className="text-sm text-slate-500">
              Reports with abnormal/critical results awaiting manual sign-off.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Back to Dashboard
          </Link>
        </div>

        {/* Queue list */}
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead className="bg-slate-100 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Patient ID</th>
                <th className="px-4 py-3">Sample</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Abnormal</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-400" colSpan={6}>
                    Loading…
                  </td>
                </tr>
              ) : pendingDisplay.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-400" colSpan={6}>
                    No reports awaiting review.
                  </td>
                </tr>
              ) : (
                pendingDisplay.map((r) => {
                  const abnormal = r.results
                    .filter((x) => x.flag === "H" || x.flag === "L")
                    .map((x) => getParam(x.parameter_name).label.split(" ")[0])
                    .join(", ");
                  return (
                    <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {r.patient?.first_name} {r.patient?.last_name}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{r.patient?.patient_id}</td>
                      <td className="px-4 py-3 text-slate-600">{r.sample_id}</td>
                      <td className="px-4 py-3 text-slate-600">{fmt(r.test_date)}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-semibold text-red-600">
                          {abnormal || "-"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => open(r.id)}
                          className="rounded-md bg-amber-600 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-700"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Review modal */}
        {selected && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl">
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">
                    {selected.patient?.first_name} {selected.patient?.last_name}
                    <span className="ml-2 text-sm font-normal text-slate-400">
                      {selected.patient?.patient_id} • {selected.sample_id}
                    </span>
                  </h2>
                  <p className="text-sm text-slate-500">
                    Requested by {selected.requested_by || "-"} • {fmt(selected.test_date)}
                  </p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="rounded-md border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50"
                >
                  Close
                </button>
              </div>

              {(["wbc", "rbc", "plt"] as const).map((grp) => {
                const rows = selected.results.filter(
                  (r) => getParam(r.parameter_name).group === grp
                );
                if (rows.length === 0) return null;
                const ordered = [...rows].sort((a, b) => order(a) - order(b));
                return (
                  <div key={grp} className="mb-4">
                    <h3 className="mb-1 text-sm font-semibold text-slate-700">
                      {GROUP_LABELS[grp]}
                    </h3>
                    <table className="w-full text-sm">
                      <thead className="text-xs uppercase text-slate-400">
                        <tr>
                          <th className="py-1 pr-2 text-left">Parameter</th>
                          <th className="py-1 px-2 text-left">Result</th>
                          <th className="py-1 px-2 text-left">Unit</th>
                          <th className="py-1 px-2 text-left">Ref Range</th>
                          <th className="py-1 pl-2 text-center">Flag</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ordered.map((r) => (
                          <tr
                            key={r.parameter_name}
                            className={`border-t border-slate-100 ${
                              r.flag === "H"
                                ? "bg-red-50/60"
                                : r.flag === "L"
                                ? "bg-blue-50/60"
                                : ""
                            }`}
                          >
                            <td className="py-1 pr-2 font-medium">
                              {getParam(r.parameter_name).label}
                            </td>
                            <td className="py-1 px-2">{r.result_value ?? "-"}</td>
                            <td className="py-1 px-2 text-slate-600">{r.unit || "-"}</td>
                            <td className="py-1 px-2 text-slate-600">
                              {r.ref_range_low ?? "-"} - {r.ref_range_high ?? "-"}
                            </td>
                            <td className="py-1 pl-2 text-center">
                              <FlagBadge flag={r.flag === "H" || r.flag === "L" ? r.flag : "normal"} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })}

              {selected.comments && (
                <div className="mb-3 rounded bg-amber-50 p-2 text-sm text-amber-900">
                  {selected.comments}
                </div>
              )}

              <div className="mt-4">
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Verification notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g. Reviewed histogram, low HGB consistent with history…"
                />
              </div>

              <div className="mt-4 flex justify-end gap-2">
                <button
                  onClick={() => signOff("revised")}
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
                >
                  Mark Revised
                </button>
                <button
                  onClick={() => signOff("reviewed")}
                  className="rounded-md bg-blue-700 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-800"
                >
                  Approve &amp; Release
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </RequireAuth>
  );
}