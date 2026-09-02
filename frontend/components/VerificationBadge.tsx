export default function VerificationBadge({ status }: { status?: string }) {
  const s = status || "auto_verified";
  if (s === "pending_review") {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-300">
        Pending Review
      </span>
    );
  }
  if (s === "reviewed" || s === "revised") {
    return (
      <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700 ring-1 ring-purple-300">
        Reviewed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700 ring-1 ring-green-300">
      Auto-verified
    </span>
  );
}