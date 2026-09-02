"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Report, ResultItem } from "@/lib/types";
import Header from "@/components/Header";
import { RequireAuth } from "@/components/Auth";
import { useToast } from "@/components/Toast";
import FormField, { inputCls } from "@/components/FormField";
import ResultEditor from "@/components/ResultEditor";
import { applyAutoCalc } from "@/lib/buildResults";
import { AUTO_CALC } from "@/lib/parameters";
import type { PanelType } from "@/lib/parameters";

function toLocalInput(s?: string) {
  if (!s) return "";
  const d = new Date(s);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

function detectPanel(results: ResultItem[]): PanelType {
  const keys = new Set(results.map((r) => r.parameter_name));
  if (keys.has("neu_pct") && (keys.has("wbc"))) return "NEU";
  return "LMG";
}

export default function EditReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [panel, setPanel] = useState<PanelType>("LMG");
  const [requestedBy, setRequestedBy] = useState("");
  const [technologist, setTechnologist] = useState("");
  const [comments, setComments] = useState("");
  const [testDate, setTestDate] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getReport(id)
      .then((r) => {
        setReport(r);
        setResults(
          [...r.results].sort(
            (a, b) =>
              a.parameter_name.length - b.parameter_name.length
          )
        );
        setPanel(detectPanel(r.results));
        setRequestedBy(r.requested_by || "");
        setTechnologist(r.technologist_name || "");
        setComments(r.comments || "");
        setTestDate(toLocalInput(r.test_date));
      })
      .catch(() => {
        toast("Failed to load report", "error");
        router.push("/");
      })
      .finally(() => setLoading(false));
  }, [id, router, toast]);

  const handlePanelChange = (p: PanelType) => {
    setPanel(p);
  };

  const handleResultChange = (key: string, updates: Partial<ResultItem>) => {
    setResults((prev) => {
      const next = prev.map((r) =>
        r.parameter_name === key ? { ...r, ...updates } : r
      );
      if (updates.result_value !== undefined && Object.keys(AUTO_CALC).includes(key)) {
        return prev; // keep manual value as-is; only recalc others
      }
      return next;
    });
  };

  const handleSave = async () => {
    if (!report) return;
    setSaving(true);
    try {
      const updated = await api.updateReport(report.id, {
        requested_by: requestedBy,
        technologist_name: technologist,
        comments,
        test_date: testDate ? new Date(testDate).toISOString() : undefined,
        results,
      });
      toast("Report updated");
      router.push(`/reports/${updated.id}`);
    } catch (e: any) {
      toast(e.message || "Failed to update report", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <RequireAuth>
        <Header />
        <main className="mx-auto max-w-6xl px-4 py-8 text-center text-slate-500">
          Loading report…
        </main>
      </RequireAuth>
    );
  }

  if (!report) return null;

  return (
    <RequireAuth>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">
          Edit Report{" "}
          <span className="text-slate-400">({report.sample_id})</span>
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          {report.patient?.first_name} {report.patient?.last_name} •{" "}
          {report.patient?.patient_id}
        </p>

        <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Details</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Date & Time of Analysis">
              <input
                type="datetime-local"
                className={inputCls}
                value={testDate}
                onChange={(e) => setTestDate(e.target.value)}
              />
            </FormField>
            <FormField label="Requested By / Referring Doctor">
              <input
                className={inputCls}
                value={requestedBy}
                onChange={(e) => setRequestedBy(e.target.value)}
              />
            </FormField>
            <FormField label="Technologist Name">
              <input
                className={inputCls}
                value={technologist}
                onChange={(e) => setTechnologist(e.target.value)}
              />
            </FormField>
          </div>
        </section>

        <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Results</h2>
          <p className="mb-3 text-xs text-slate-500">
            Editable reference ranges and units. Flags recompute automatically.
          </p>
          <ResultEditor
            results={results}
            panel={panel}
            onPanelChange={handlePanelChange}
            onResultChange={handleResultChange}
          />
        </section>

        <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            Comments / Remarks
          </h2>
          <textarea
            className={inputCls}
            rows={3}
            value={comments}
            onChange={(e) => setComments(e.target.value)}
          />
        </section>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => router.push(`/reports/${report.id}`)}
            className="rounded-md border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </main>
    </RequireAuth>
  );
}