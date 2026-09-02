"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, downloadPdf } from "@/lib/api";
import type { Report } from "@/lib/types";
import { backendResultsToReportParams } from "@/lib/reportParams";
import Header from "@/components/Header";
import { RequireAuth } from "@/components/Auth";
import { useToast } from "@/components/Toast";
import VerificationBadge from "@/components/VerificationBadge";
import HaematologyReport from "@/components/HaematologyReport";
import type { PatientFields } from "@/components/HaematologyReport/PatientInfoForm";

function formatDate(s?: string) {
  if (!s) return "-";
  return new Date(s).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ReportViewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getReport(id)
      .then((r) => setReport(r))
      .catch((e) => {
        toast(e.message || "Failed to load report", "error");
        router.push("/");
      })
      .finally(() => setLoading(false));
  }, [id, router, toast]);

  if (loading) {
    return (
      <RequireAuth>
        <Header />
        <main className="mx-auto max-w-4xl px-4 py-8 text-center text-slate-500">
          Loading report…
        </main>
      </RequireAuth>
    );
  }

  if (!report) return null;

  // Build patient fields from the backend report data.
  const patient: Partial<PatientFields> = {
    name: report.patient
      ? `${report.patient.first_name} ${report.patient.last_name}`
      : "",
    gender: report.patient?.gender ?? "",
    age: report.patient?.age != null ? `${report.patient.age} Year` : "",
    pid: report.patient?.patient_id ?? "",
    sample: report.sample_id ?? "",
    date: formatDate(report.test_date),
    requestedBy: report.requested_by ?? "",
  };

  // Map backend result parameter names to reportParams keys (WBC, NEU, etc.).
  const params = backendResultsToReportParams(report.results);

  return (
    <RequireAuth>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-8">
        {/* Toolbar */}
        <div className="no-print mb-4 flex flex-wrap gap-2">
          <button
            onClick={() => downloadPdf(report.id)}
            className="rounded-md border border-blue-700 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50"
          >
            Download PDF
          </button>
          <Link
            href={`/reports/${report.id}/edit`}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Edit
          </Link>
          <Link
            href="/"
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Back to Dashboard
          </Link>
        </div>

        {/* Verification badge */}
        <div className="mb-3 flex items-center gap-2">
          <VerificationBadge status={report.verification_status} />
          {report.verification_notes && (
            <span className="text-xs text-slate-500">
              {report.verification_notes}
            </span>
          )}
        </div>

        {/* Render the haematology report with side-by-side layout */}
        <HaematologyReport
          patient={patient}
          params={params}
          comments={report.comments ?? ""}
        />
      </main>
    </RequireAuth>
  );
}