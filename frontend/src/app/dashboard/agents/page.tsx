"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { Agent, User, api, clearToken, formatDuration } from "@/lib/api";

export default function AgentsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [me, ag] = await Promise.all([
          api<User>("/api/auth/me"),
          api<Agent[]>("/api/agents"),
        ]);
        setUser(me);
        setAgents(ag);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [router]);

  return (
    <DashboardShell userName={user?.name}>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl">Agents</h1>
          <p className="mt-2 text-[var(--muted)]">All voice agents across your businesses.</p>
        </div>
        <Link
          href="/dashboard/agents/new"
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm text-white"
        >
          New agent
        </Link>
      </div>
      <div className="mt-8 overflow-hidden rounded-xl border border-[var(--line)] bg-white/80">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--line)] text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 font-medium">Agent</th>
              <th className="px-4 py-3 font-medium">Business</th>
              <th className="px-4 py-3 font-medium">Phone</th>
              <th className="px-4 py-3 font-medium">Calls</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-3">
                  <Link href={`/dashboard/agents/${a.id}`} className="font-medium hover:underline">
                    {a.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">{a.business_name}</td>
                <td className="px-4 py-3">{a.phone_number || "Not connected"}</td>
                <td className="px-4 py-3">
                  {a.call_count} · {formatDuration(a.avg_duration_seconds)}
                </td>
                <td className="px-4 py-3 capitalize">{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardShell>
  );
}
