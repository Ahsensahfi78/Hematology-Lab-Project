export type Gender = "Male" | "Female";
export type Flag = "H" | "L" | "normal";

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  gender: Gender;
  age: number;
  patient_id: string;
  created_at?: string;
}

export interface ResultItem {
  id?: number;
  report_id?: number;
  parameter_name: string;
  result_value: number | null;
  unit: string;
  ref_range_low: number | null;
  ref_range_high: number | null;
  flag: Flag;
}

export interface Report {
  id: number;
  patient_id: number;
  sample_id: string;
  test_date?: string;
  requested_by?: string;
  technologist_name?: string;
  comments?: string;
  verification_status?: string;
  verification_notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  source?: string;
  created_at?: string;
  patient?: Patient;
  results: ResultItem[];
}

export interface ParameterMeta {
  key: string;
  label: string;
  unit: string;
  group: string;
  description?: string;
}

export interface PatientCreate {
  first_name: string;
  last_name: string;
  gender: Gender;
  age: number;
}

export interface ReportCreate {
  patient_id: number;
  requested_by?: string;
  technologist_name?: string;
  comments?: string;
  test_date?: string;
  panel_type: "LMG" | "NEU";
  results: ResultItem[];
}
