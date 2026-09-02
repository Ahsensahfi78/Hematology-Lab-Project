// Lab letterhead header for the printable report (A4 width).
export default function ReportHeader() {
  return (
    <div className="mb-4 flex items-start justify-between border-b-2 border-blue-900 pb-3">
      <div>
        <div className="text-[11px] font-bold tracking-wide text-[#b5342b]">
          CONFIDENTIAL REPORT
        </div>
        <div className="mt-0.5 text-2xl font-bold text-blue-900">
          LAB MEDI SCREEN
        </div>
        <div className="mb-1 inline-block rounded-sm bg-[#b5342b] px-2.5 py-0.5 text-xs font-semibold text-white">
          MEDICAL DIAGNOSTIC LABORATORY
        </div>
        <div className="text-[11.5px] leading-normal text-slate-600">
          Main Lab: 524/A, Hospital Road, Sainthamaruthu-07, Sri Lanka
          <br />
          Branch: 609, Maligaikadu Junction, Sainthamaruthu-16
          <br />
          Tel: 067 2225026 &nbsp;|&nbsp; Mobile: 077 6110098
        </div>
      </div>
      <div className="max-w-[230px] text-right text-[11px] text-slate-600">
        Member of<br />
        <strong>Qualicheck Path — Agappe Diagnostics (Switzerland)</strong><br />
        labmediscreen@gmail.com
      </div>
    </div>
  );
}