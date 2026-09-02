import type { Flag } from "@/lib/types";

export default function FlagBadge({ flag }: { flag: Flag }) {
  if (flag === "H") {
    return (
      <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-red-200">
        H
      </span>
    );
  }
  if (flag === "L") {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-200">
        L
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700 ring-1 ring-green-200">
      N
    </span>
  );
}
