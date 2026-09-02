"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "./Auth";

export default function Header() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const link = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
          active
            ? "bg-blue-700 text-white"
            : "text-blue-100 hover:bg-blue-700/50"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="no-print bg-blue-800 text-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-lg font-semibold">
            Hematology Lab
          </Link>
          <nav className="flex gap-1">
            {link("/", "Dashboard")}
            {link("/new-report", "New Report")}
            {link("/review", "Review")}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-sm text-blue-200">Logged in: {user}</span>
          )}
          <button
            onClick={logout}
            className="rounded-md bg-blue-700 px-3 py-1.5 text-sm font-medium hover:bg-blue-600"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
