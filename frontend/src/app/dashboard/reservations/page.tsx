"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { User, api, clearToken } from "@/lib/api";

type Reservation = {
  id: number;
  customer_name: string;
  phone: string | null;
  party_size: number;
  date: string;
  time: string;
  status: string;
  source: string;
  service: string | null;
};

export default function ReservationsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<Reservation[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [me, list] = await Promise.all([
          api<User>("/api/auth/me"),
          api<Reservation[]>("/api/reservations"),
        ]);
        setUser(me);
        setRows(list);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }
    load();
  }, [router]);

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Reservations</h1>
      <p className="mt-2 text-[var(--muted)]">
        Bookings from voice, test chat, and the public booking widget — one floor schedule.
      </p>

      <div className="mt-8 overflow-hidden rounded-xl border border-[var(--line)] bg-white/80">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--line)] text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 font-medium">Guest</th>
              <th className="px-4 py-3 font-medium">Party</th>
              <th className="px-4 py-3 font-medium">When</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-[var(--muted)]">
                  No reservations yet. Use Test Agent or{" "}
                  <Link href="/dashboard/agents" className="underline">
                    booking widget
                  </Link>
                  .
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium">{r.customer_name}</div>
                  <div className="text-[var(--muted)]">{r.phone || "—"}</div>
                </td>
                <td className="px-4 py-3">{r.party_size || 1}</td>
                <td className="px-4 py-3">
                  {r.date} · {String(r.time).slice(0, 5)}
                </td>
                <td className="px-4 py-3 capitalize">{r.source || "voice"}</td>
                <td className="px-4 py-3 capitalize">{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardShell>
  );
}
