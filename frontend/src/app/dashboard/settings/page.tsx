"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { Agent, User, api, clearToken } from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5050";

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

  const primary = agents[0];

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Settings</h1>
      <p className="mt-2 text-[var(--muted)]">Telephony webhook and agent defaults for the MVP.</p>

      <section className="mt-8 max-w-2xl space-y-4 rounded-2xl border border-[var(--line)] bg-white/80 p-6 text-sm">
        <h2 className="text-lg font-medium">Twilio webhook</h2>
        <p className="text-[var(--muted)]">
          In Twilio Console → your number → Voice → A call comes in, set:
        </p>
        <code className="block overflow-x-auto rounded-md bg-black/[0.04] p-3">
          {apiUrl.replace("http://", "https://").includes("localhost")
            ? "https://YOUR_NGROK_URL/telephony/incoming"
            : `${apiUrl}/telephony/incoming`}
        </code>
        {primary && (
          <p className="text-[var(--muted)]">
            Optional agent routing: append{" "}
            <code>?agent_id={primary.id}</code>
          </p>
        )}
      </section>

      <section className="mt-6 max-w-2xl rounded-2xl border border-[var(--line)] bg-white/80 p-6 text-sm">
        <h2 className="text-lg font-medium">Account</h2>
        <p className="mt-2">{user?.name}</p>
        <p className="text-[var(--muted)]">{user?.email}</p>
      </section>
    </DashboardShell>
  );
}
