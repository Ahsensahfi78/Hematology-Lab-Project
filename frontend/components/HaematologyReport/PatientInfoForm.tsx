"use client";

// Patient info in a compact 2-column grid matching the reference printed report.

export interface PatientFields {
  name: string;
  gender: string;
  age: string;
  pid: string;
  sample: string;
  date: string;
  requestedBy: string;
}

interface Props {
  fields: PatientFields;
  onChange: (next: PatientFields) => void;
}

export default function PatientInfoForm({ fields, onChange }: Props) {
  function set(key: keyof PatientFields, value: string) {
    onChange({ ...fields, [key]: value });
  }

  const row = (label: string, key: keyof PatientFields) => (
    <div className="flex items-baseline gap-1">
      <label className="w-20 shrink-0 text-[12px] font-semibold text-slate-700">
        {label}:
      </label>
      <input
        value={fields[key]}
        onChange={(e) => set(key, e.target.value)}
        className="min-w-0 flex-1 border-b border-slate-200 bg-transparent px-0.5 py-0.5 text-[12px] text-slate-800 transition-colors focus:border-blue-900 focus:outline-none"
      />
    </div>
  );

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-0.5 text-[12px]">
      {row("Name", "name")}
      {row("Sample ID", "sample")}
      {row("Gender", "gender")}
      {row("Patient ID", "pid")}
      {row("Age", "age")}
      {row("Date", "date")}
      {row("Requested by", "requestedBy")}
    </div>
  );
}