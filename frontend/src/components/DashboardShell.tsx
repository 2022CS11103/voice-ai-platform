"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/agents", label: "Agents" },
  { href: "/dashboard/calls", label: "Calls" },
  { href: "/dashboard/reservations", label: "Reservations" },
  { href: "/dashboard/guests", label: "Guests" },
  { href: "/dashboard/analytics", label: "Analytics" },
  { href: "/dashboard/settings", label: "Settings" },
];

export function DashboardShell({
  children,
  userName,
}: {
  children: React.ReactNode;
  userName?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top_left,_rgba(42,157,143,0.12),_transparent_45%),radial-gradient(ellipse_at_bottom_right,_rgba(11,31,42,0.08),_transparent_40%)]" />
      <div className="relative mx-auto flex min-h-screen max-w-6xl gap-8 px-5 py-6 md:px-8">
        <aside className="hidden w-52 shrink-0 md:block">
          <Link href="/" className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
            Vela<span className="text-[var(--accent)]">Voice</span>
          </Link>
          <p className="mt-1 text-xs text-[var(--muted)]">AI receptionist platform</p>
          <nav className="mt-10 flex flex-col gap-1">
            {links.map((link) => {
              const active =
                pathname === link.href ||
                (link.href !== "/dashboard" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-2 text-sm transition ${
                    active
                      ? "bg-[var(--ink)] text-white"
                      : "text-[var(--muted)] hover:bg-black/5 hover:text-[var(--ink)]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            onClick={() => {
              clearToken();
              router.push("/login");
            }}
            className="mt-10 text-sm text-[var(--muted)] hover:text-[var(--ink)]"
          >
            Sign out
          </button>
        </aside>

        <main className="relative flex-1 pb-16">
          <header className="mb-8 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-[var(--muted)]">
                {userName ? `Good day, ${userName}` : "Your workspace"}
              </p>
            </div>
            <Link
              href="/dashboard/agents/new"
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:brightness-110"
            >
              + Create Agent
            </Link>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}
