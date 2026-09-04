"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { User, api, clearToken } from "@/lib/api";

type Guest = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  preferences: string | null;
  visit_count: number;
  notes: string | null;
};

export default function GuestsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [guests, setGuests] = useState<Guest[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [me, list] = await Promise.all([
          api<User>("/api/auth/me"),
          api<Guest[]>("/api/guests"),
        ]);
        setUser(me);
        setGuests(list);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [router]);

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Guests</h1>
      <p className="mt-2 text-[var(--muted)]">
        Shared guest brain — voice agent and staff see the same people, preferences, and visits.
      </p>

      <div className="mt-8 divide-y divide-[var(--line)] overflow-hidden rounded-xl border border-[var(--line)] bg-white/80">
        {guests.length === 0 && (
          <div className="px-5 py-10 text-sm text-[var(--muted)]">
            Guests appear after a booking captures name/phone.
          </div>
        )}
        {guests.map((g) => (
          <div key={g.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div>
              <div className="font-medium">{g.name}</div>
              <div className="text-sm text-[var(--muted)]">
                {g.phone || "No phone"} · {g.email || "No email"}
              </div>
              {g.preferences && (
                <div className="mt-1 text-sm text-[var(--muted)]">Prefs: {g.preferences}</div>
              )}
            </div>
            <div className="text-sm">
              <span className="rounded-full bg-black/5 px-2.5 py-1">
                {g.visit_count} visit{g.visit_count === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
