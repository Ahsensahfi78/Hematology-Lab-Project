"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Patient, ResultItem } from "@/lib/types";
import Header from "@/components/Header";
import { RequireAuth } from "@/components/Auth";
import { useToast } from "@/components/Toast";
import FormField, { inputCls } from "@/components/FormField";
import ResultEditor from "@/components/ResultEditor";
import { buildResults, rebuildForPanel, applyAutoCalc } from "@/lib/buildResults";
import { AUTO_CALC } from "@/lib/parameters";
import type { PanelType } from "@/lib/parameters";

const TODAY = new Date();
const LOCAL = new Date(TODAY.getTime() - TODAY.getTimezoneOffset() * 60000)
  .toISOString()
  .slice(0, 16);

export default function NewReportPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [existingPatients, setExistingPatients] = useState<Patient[]>([]);
  const [mode, setMode] = useState<"new" | "existing">("new");
  const [selectedPatient, setSelectedPatient] = useState<number | "">("");

  // patient fields
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [gender, setGender] = useState<"Male" | "Female">("Male");
  const [age, setAge] = useState<number | "">("");

  // report fields
  const [panel, setPanel] = useState<PanelType>("LMG");
  const [requestedBy, setRequestedBy] = useState("");
  const [technologist, setTechnologist] = useState("");
  const [comments, setComments] = useState("");
  const [testDate, setTestDate] = useState(LOCAL);

  const [results, setResults] = useState<ResultItem[]>([]);
  const [manualOverride, setManualOverride] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .listPatients()
      .then(setExistingPatients)
      .catch(() => {});
  }, []);

  const ageNum = age === "" ? 0 : Number(age);

  // Build results when patient age/gender defined
  useEffect(() => {
    if (age !== "" && gender) {
      setResults(buildResults(panel, ageNum, gender));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePatientMetaChange = () => {
    if (age !== "" && gender) {
      setResults((prev) => {
        const rebuilt = rebuildForPanel(panel, ageNum, gender, prev);
        return applyAutoCalc(rebuilt, manualOverride);
      });
    }
  };

  const handlePanelChange = (p: PanelType) => {
    setPanel(p);
    setResults((prev) =>
      applyAutoCalc(rebuildForPanel(p, ageNum, gender, prev), manualOverride)
    );
  };

  const handleResultChange = (key: string, updates: Partial<ResultItem>) => {
    if (updates.result_value !== undefined) {
      // manual override tracking for auto-calc fields
      if (Object.keys(AUTO_CALC).includes(key)) {
        setManualOverride((s) => {
          const next = new Set(s);
          next.add(key);
          return next;
        });
      }
    }
    setResults((prev) => {
      const next = prev.map((r) =>
        r.parameter_name === key ? { ...r, ...updates } : r
      );
      let out = next;
      if (updates.result_value !== undefined) {
        out = applyAutoCalc(next, manualOverride);
      }
      return out;
    });
  };

  const validate = () => {
    if (mode === "new") {
      if (!firstName.trim() || !lastName.trim()) return "First and last name are required.";
      if (age === "" || Number(age) < 0) return "Please enter a valid age.";
    } else {
      if (selectedPatient === "") return "Please select a patient.";
    }
    return null;
  };

  const handleSave = async () => {
    const err = validate();
    if (err) {
      toast(err, "error");
      return;
    }

    setSaving(true);
    try {
      let patientId: number;
      if (mode === "new") {
        const patient = await api.createPatient({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          gender,
          age: Number(age),
        });
        patientId = patient.id;
      } else {
        patientId = Number(selectedPatient);
      }

      const report = await api.createReport({
        patient_id: patientId,
        requested_by: requestedBy || undefined,
        technologist_name: technologist || undefined,
        comments: comments || undefined,
        test_date: testDate ? new Date(testDate).toISOString() : undefined,
        panel_type: panel,
        results,
      });
      toast("Report saved successfully");
      router.push(`/reports/${report.id}`);
    } catch (e: any) {
      toast(e.message || "Failed to save report", "error");
    } finally {
      setSaving(false);
    }
  };

  const loadingPatients = existingPatients.length === 0;

  return (
    <RequireAuth>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">New Report</h1>
        <p className="mb-6 text-sm text-slate-500">
          Enter patient details and haematology panel results.
        </p>

        <form onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
          {/* Patient section */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-4">
              <h2 className="text-lg font-semibold text-slate-800">Patient</h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setMode("new")}
                  className={`rounded-md px-3 py-1 text-sm font-medium ${
                    mode === "new"
                      ? "bg-blue-700 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  New patient
                </button>
                <button
                  type="button"
                  onClick={() => setMode("existing")}
                  className={`rounded-md px-3 py-1 text-sm font-medium ${
                    mode === "existing"
                      ? "bg-blue-700 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  Existing patient
                </button>
              </div>
            </div>

            {mode === "new" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <FormField label="First Name">
                  <input className={inputCls} value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                </FormField>
                <FormField label="Last Name">
                  <input className={inputCls} value={lastName} onChange={(e) => setLastName(e.target.value)} />
                </FormField>
                <FormField label="Gender">
                  <select className={inputCls} value={gender} onChange={(e) => { setGender(e.target.value as any); handlePatientMetaChange(); }}>
                    <option>Male</option>
                    <option>Female</option>
                  </select>
                </FormField>
                <FormField label="Age (years)" hint="Below 14 uses pediatric reference ranges.">
                  <input className={inputCls} type="number" min={0} max={120} value={age} onChange={(e) => { setAge(e.target.value === "" ? "" : Number(e.target.value)); handlePatientMetaChange(); }} />
                </FormField>
              </div>
            ) : (
              <div>
                {loadingPatients ? (
                  <p className="text-sm text-slate-400">Loading patients…</p>
                ) : (
                  <select className={inputCls} value={selectedPatient} onChange={(e) => setSelectedPatient(e.target.value === "" ? "" : Number(e.target.value))}>
                    <option value="">Select a patient…</option>
                    {existingPatients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.patient_id} — {p.first_name} {p.last_name} ({p.age}, {p.gender})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </section>

          {/* Report metadata */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">Report Details</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <FormField label="Date & Time of Analysis" hint="Defaults to now.">
                <input type="datetime-local" className={inputCls} value={testDate} onChange={(e) => setTestDate(e.target.value)} />
              </FormField>
              <FormField label="Requested By / Referring Doctor">
                <input className={inputCls} value={requestedBy} onChange={(e) => setRequestedBy(e.target.value)} />
              </FormField>
              <FormField label="Technologist Name">
                <input className={inputCls} value={technologist} onChange={(e) => setTechnologist(e.target.value)} />
              </FormField>
            </div>
          </section>

          {/* Results section */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-800">Haematology Results</h2>
              <span className="text-xs text-slate-400">
                {age !== "" && gender ? "Ranges adjusted for patient" : "Enter age to auto-adjust ranges"}
              </span>
            </div>
            <p className="mb-4 text-xs text-slate-500">
              HCT, MCH, and MCHC are auto-calculated from related values; type
              over them to enter a manual result.
            </p>
            <ResultEditor
              results={results}
              panel={panel}
              onPanelChange={handlePanelChange}
              onResultChange={handleResultChange}
            />
          </section>

          {/* Comments */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">Comments / Remarks</h2>
            <textarea
              className={inputCls}
              rows={3}
              placeholder="e.g. Low platelet count, borderline MCV, smear review recommended…"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
            />
          </section>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => router.push("/")}
              className="rounded-md border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save Report"}
            </button>
          </div>
        </form>
      </main>
    </RequireAuth>
  );
}