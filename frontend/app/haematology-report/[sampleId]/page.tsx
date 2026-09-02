import HaematologyReport from "@/components/HaematologyReport";

// Standalone haematology report renderer.
//
// Route: /haematology-report/[sampleId]
//   - Renders the reusable <HaematologyReport /> client component.
//   - The component accepts `patient` / `params` props. Today it defaults to
//     reference sample data; once the backend HL7/ASTM ingestion is wired, the
//     caller can pass analyzer-derived patient fields + parameter values here.
//
// This page intentionally does NOT require auth so it can also be printed as a
// static record. Keep it separate from /reports/[id] (the stored-report viewer).

interface Props {
  params: Promise<{ sampleId: string }>;
}

export default async function HaematologyReportPage({ params }: Props) {
  const { sampleId } = await params;

  // Reference defaults live inside the component; pass sampleId so it can be
  // pre-filled/served later from the ingestion layer.
  const patient = { sample: sampleId };

  return (
    <div className="bg-[#eef1f4] py-6">
      <HaematologyReport patient={patient} />
    </div>
  );
}