"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import {
  Agent,
  Analytics,
  User,
  api,
  clearToken,
  formatDuration,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [me, ag, an] = await Promise.all([
          api<User>("/api/auth/me"),
          api<Agent[]>("/api/agents"),
          api<Analytics>("/api/analytics"),
        ]);
        setUser(me);
        setAgents(ag);
        setAnalytics(an);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load().catch((e) => setError(String(e)));
  }, [router]);

  return (
    <DashboardShell userName={user?.name}>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Your AI Agents</h1>
      <p className="mt-2 text-[var(--muted)]">
        Configure inbound receptionists, knowledge, and phone connectivity.
      </p>

      {analytics && (
        <div className="mt-8 grid gap-3 sm:grid-cols-4">
          {[
            ["Total calls", analytics.total_calls],
            ["Appointments", analytics.appointments],
            ["Leads", analytics.leads_captured],
            ["Avg duration", formatDuration(analytics.avg_duration_seconds)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-[var(--line)] bg-white/70 p-4">
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
              <div className="mt-2 text-2xl font-medium">{value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="rounded-2xl border border-[var(--line)] bg-white/80 p-6"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-medium">{agent.name}</h2>
                <p className="text-sm text-[var(--muted)]">{agent.business_name}</p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {agent.status}
              </span>
            </div>
            <dl className="mt-5 grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="text-[var(--muted)]">Calls</dt>
                <dd className="mt-1 font-medium">{agent.call_count}</dd>
              </div>
              <div>
                <dt className="text-[var(--muted)]">Avg duration</dt>
                <dd className="mt-1 font-medium">{formatDuration(agent.avg_duration_seconds)}</dd>
              </div>
              <div>
                <dt className="text-[var(--muted)]">Success</dt>
                <dd className="mt-1 font-medium">{Math.round(agent.success_rate)}%</dd>
              </div>
            </dl>
            <div className="mt-5 flex flex-wrap gap-2">
              {agent.phone_number && (
                <a
                  href={`tel:${agent.phone_number.replace(/\s/g, "")}`}
                  className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm text-white"
                >
                  Call {agent.phone_number}
                </a>
              )}
              <Link
                href={`/dashboard/agents/${agent.id}`}
                className="inline-block rounded-md bg-[var(--ink)] px-4 py-2 text-sm text-white"
              >
                Open Agent
              </Link>
            </div>
          </div>
        ))}
        <Link
          href="/dashboard/agents/new"
          className="flex min-h-48 items-center justify-center rounded-2xl border border-dashed border-[var(--line)] text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
        >
          + Create Agent
        </Link>
      </div>
    </DashboardShell>
  );
}
