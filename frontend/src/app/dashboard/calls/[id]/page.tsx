"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { CallDetail, User, api, clearToken, formatDuration } from "@/lib/api";

export default function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [call, setCall] = useState<CallDetail | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [me, detail] = await Promise.all([
          api<User>("/api/auth/me"),
          api<CallDetail>(`/api/calls/${params.id}`),
        ]);
        setUser(me);
        setCall(detail);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [params.id, router]);

  if (!call) {
    return (
      <DashboardShell>
        <p className="text-[var(--muted)]">Loading call…</p>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Call Details</h1>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Duration", formatDuration(call.duration_seconds)],
          ["Status", call.status],
          ["Outcome", call.outcome || "—"],
          ["Sentiment", call.sentiment || "—"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-[var(--line)] bg-white/80 p-4">
            <div className="text-xs text-[var(--muted)]">{k}</div>
            <div className="mt-1 font-medium capitalize">{v}</div>
          </div>
        ))}
      </div>

      <section className="mt-8 rounded-xl border border-[var(--line)] bg-white/80 p-5">
        <h2 className="font-medium">Summary</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{call.summary || "No summary yet."}</p>
        <p className="mt-4 text-sm">
          <span className="text-[var(--muted)]">Intent:</span> {call.intent || "—"}
        </p>
      </section>

      <section className="mt-8">
        <h2 className="font-medium">Transcript</h2>
        <div className="mt-4 space-y-3">
          {call.messages.length === 0 && (
            <p className="text-sm text-[var(--muted)]">Transcript will appear after the call ends.</p>
          )}
          {call.messages.map((m) => (
            <div
              key={m.id}
              className={`rounded-xl px-4 py-3 text-sm ${
                m.role === "ai"
                  ? "bg-[#e7f6f3]"
                  : m.role === "customer"
                    ? "bg-white border border-[var(--line)]"
                    : "bg-black/5 text-[var(--muted)]"
              }`}
            >
              <div className="mb-1 text-xs uppercase tracking-wide opacity-60">{m.role}</div>
              {m.content}
            </div>
          ))}
        </div>
      </section>
    </DashboardShell>
  );
}
