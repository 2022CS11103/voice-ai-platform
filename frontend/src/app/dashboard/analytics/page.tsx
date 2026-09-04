"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { Analytics, User, api, clearToken, formatDuration } from "@/lib/api";

export default function AnalyticsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [me, analytics] = await Promise.all([
          api<User>("/api/auth/me"),
          api<Analytics>("/api/analytics"),
        ]);
        setUser(me);
        setData(analytics);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [router]);

  const cards = data
    ? [
        ["Total calls", data.total_calls],
        ["Successful calls", data.successful_calls],
        ["Transferred", data.transferred],
        ["Failed", data.failed],
        ["Avg duration", formatDuration(data.avg_duration_seconds)],
        ["Appointments", data.appointments],
        ["Leads captured", data.leads_captured],
      ]
    : [];

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Analytics</h1>
      <p className="mt-2 text-[var(--muted)]">Production-oriented call and conversion metrics.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={String(label)} className="rounded-2xl border border-[var(--line)] bg-white/80 p-5">
            <div className="text-sm text-[var(--muted)]">{label}</div>
            <div className="mt-3 font-[family-name:var(--font-display)] text-3xl">{value}</div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
