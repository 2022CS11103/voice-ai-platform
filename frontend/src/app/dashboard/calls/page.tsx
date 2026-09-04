"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { CallItem, User, api, clearToken, formatDuration } from "@/lib/api";

export default function CallsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [calls, setCalls] = useState<CallItem[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [me, list] = await Promise.all([
          api<User>("/api/auth/me"),
          api<CallItem[]>("/api/calls"),
        ]);
        setUser(me);
        setCalls(list);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [router]);

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Call History</h1>
      <p className="mt-2 text-[var(--muted)]">Transcripts, outcomes, and summaries from inbound calls.</p>

      <div className="mt-8 divide-y divide-[var(--line)] overflow-hidden rounded-xl border border-[var(--line)] bg-white/80">
        {calls.length === 0 && (
          <div className="px-5 py-10 text-sm text-[var(--muted)]">
            No calls yet. Point your Twilio number webhook to{" "}
            <code className="rounded bg-black/5 px-1">/telephony/incoming</code> and place a test call.
          </div>
        )}
        {calls.map((call) => (
          <Link
            key={call.id}
            href={`/dashboard/calls/${call.id}`}
            className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition hover:bg-black/[0.02]"
          >
            <div>
              <div className="font-medium">
                {call.agent_name || "Agent"} · {call.caller_number || "Unknown caller"}
              </div>
              <div className="mt-1 text-sm text-[var(--muted)]">
                {new Date(call.started_at).toLocaleString()} · {formatDuration(call.duration_seconds)}
              </div>
            </div>
            <div className="text-sm">
              <span className="rounded-full bg-black/5 px-2.5 py-1">
                {call.outcome || call.status}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </DashboardShell>
  );
}
