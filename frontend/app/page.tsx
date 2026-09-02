"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Report } from "@/lib/types";
import Header from "@/components/Header";
import { RequireAuth } from "@/components/Auth";
import { useToast } from "@/components/Toast";
import VerificationBadge from "@/components/VerificationBadge";

function formatDate(s?: string) {
  if (!s) return "-";
  const d = new Date(s);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const load = useCallback(
    async (query?: string) => {
      setLoading(true);
      try {
        const data = await api.listReports(query);
        setReports(data);
      } catch (err: any) {
        toast(err.message || "Failed to load reports", "error");
      } finally {
        setLoading(false);
      }
    },
    [toast]
  );

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this report? This cannot be undone.")) return;
    try {
      await api.deleteReport(id);
      setReports((r) => r.filter((x) => x.id !== id));
      toast("Report deleted");
    } catch (err: any) {
      toast(err.message || "Delete failed", "error");
    }
  };

  return (
    <RequireAuth>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
            <p className="text-sm text-slate-500">
              {reports.length} saved report{reports.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="flex gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") load(q);
              }}
              placeholder="Search name, ID, sample…"
              className="w-64 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={() => load(q)}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Search
            </button>
            <Link
              href="/new-report"
              className="rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              + New Report
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="rounded-lg bg-white p-10 text-center text-slate-500 shadow-sm">
            Loading reports…
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-lg bg-white p-10 text-center shadow-sm">
            <p className="text-slate-500">No reports yet.</p>
            <Link
              href="/new-report"
              className="mt-3 inline-block rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
            >
              Create your first report
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left">
              <thead className="bg-slate-100 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Patient ID</th>
                  <th className="px-4 py-3">Sample ID</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Verification</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr
                    key={r.id}
                    className="border-t border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {r.patient?.first_name} {r.patient?.last_name}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {r.patient?.patient_id}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.sample_id}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatDate(r.test_date)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                          (r.source || "manual") === "manual"
                            ? "bg-slate-100 text-slate-500"
                            : (r.source || "") === "hl7"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-teal-100 text-teal-700"
                        }`}
                      >
                        {r.source || "manual"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <VerificationBadge status={r.verification_status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        <Link
                          href={`/reports/${r.id}`}
                          className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-100"
                        >
                          View
                        </Link>
                        <Link
                          href={`/reports/${r.id}/edit`}
                          className="rounded-md border border-blue-300 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="rounded-md border border-red-300 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </RequireAuth>
  );
}
