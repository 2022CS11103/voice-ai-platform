"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5050";

type Biz = { id: number; name: string; industry: string; address?: string };

export default function PublicBookingPage() {
  const params = useParams<{ businessId: string }>();
  const businessId = Number(params.businessId);
  const [biz, setBiz] = useState<Biz | null>(null);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [slots, setSlots] = useState<string[]>([]);
  const [time, setTime] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [party, setParty] = useState(2);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/api/public/businesses/${businessId}`)
      .then((r) => r.json())
      .then(setBiz)
      .catch(() => setError("Business not found"));
  }, [businessId]);

  useEffect(() => {
    if (!date) return;
    fetch(`${API}/api/public/businesses/${businessId}/availability`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date }),
    })
      .then((r) => r.json())
      .then((data) => {
        setSlots(data.slots || []);
        setTime("");
      })
      .catch(() => setSlots([]));
  }, [businessId, date]);

  async function book(e: FormEvent) {
    e.preventDefault();
    setError("");
    setStatus("");
    try {
      const res = await fetch(`${API}/api/public/businesses/${businessId}/book`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: name,
          phone,
          party_size: party,
          date,
          time,
        }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Booking failed");
      setStatus(`Booked! ${body.customer_name} · ${body.date} at ${String(body.time).slice(0, 5)}`);
      setName("");
      setPhone("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] px-5 py-12 text-[var(--ink)]">
      <div className="mx-auto max-w-lg">
        <p className="text-sm text-[var(--accent)]">Book online</p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl">
          {biz?.name || "Loading…"}
        </h1>
        <p className="mt-2 text-[var(--muted)]">
          Same availability engine the voice agent uses — pick a time and we&apos;ll seat you.
        </p>

        <form
          onSubmit={book}
          className="mt-8 space-y-4 rounded-2xl border border-[var(--line)] bg-white/90 p-6"
        >
          <label className="block text-sm">
            Date
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Party size
            <input
              type="number"
              min={1}
              max={20}
              className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={party}
              onChange={(e) => setParty(Number(e.target.value))}
            />
          </label>
          <fieldset className="text-sm">
            <legend className="mb-2">Available times</legend>
            <div className="flex flex-wrap gap-2">
              {slots.length === 0 && (
                <span className="text-[var(--muted)]">No open slots this day</span>
              )}
              {slots.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setTime(s)}
                  className={`rounded-md px-3 py-1.5 ${
                    time === s
                      ? "bg-[var(--ink)] text-white"
                      : "border border-[var(--line)] bg-white"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm">
            Name
            <input
              className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Phone
            <input
              className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {status && <p className="text-sm text-emerald-700">{status}</p>}
          <button
            type="submit"
            disabled={!time}
            className="w-full rounded-md bg-[var(--accent)] py-3 text-sm font-semibold text-white disabled:opacity-40"
          >
            Confirm reservation
          </button>
        </form>
      </div>
    </div>
  );
}
