"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { Agent, User, api, clearToken } from "@/lib/api";

const steps = ["Business", "Capabilities", "Personality"];

export default function NewAgentPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [businessName, setBusinessName] = useState("ABC Dental Clinic");
  const [industry, setIndustry] = useState("healthcare");
  const [agentName, setAgentName] = useState("Sarah");
  const [purpose, setPurpose] = useState("Handle patient inquiries and appointment booking");
  const [caps, setCaps] = useState({
    answer_questions: true,
    book_appointments: true,
    capture_leads: true,
    transfer_calls: false,
    take_orders: false,
  });
  const [personality, setPersonality] = useState("friendly");
  const [voice, setVoice] = useState("alloy");
  const [greeting, setGreeting] = useState(
    "Hi! Thanks for calling ABC Dental. How can I help you today?",
  );

  useEffect(() => {
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => {
        clearToken();
        router.replace("/login");
      });
  }, [router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (step < 2) {
      setStep(step + 1);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const agent = await api<Agent>("/api/agents", {
        method: "POST",
        body: JSON.stringify({
          business_name: businessName,
          industry,
          agent_name: agentName,
          purpose,
          personality,
          voice,
          greeting,
          capabilities: caps,
        }),
      });
      router.push(`/dashboard/agents/${agent.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <DashboardShell userName={user?.name}>
      <h1 className="font-[family-name:var(--font-display)] text-3xl">Create your AI Agent</h1>
      <div className="mt-4 flex gap-2 text-sm">
        {steps.map((label, i) => (
          <span
            key={label}
            className={`rounded-full px-3 py-1 ${
              i === step ? "bg-[var(--ink)] text-white" : "bg-black/5 text-[var(--muted)]"
            }`}
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>

      <form onSubmit={submit} className="mt-8 max-w-xl space-y-4 rounded-2xl border border-[var(--line)] bg-white/80 p-6">
        {step === 0 && (
          <>
            <label className="block text-sm">
              Business name
              <input
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Industry
              <select
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
              >
                <option value="healthcare">Healthcare</option>
                <option value="salon">Salon</option>
                <option value="restaurant">Restaurant</option>
                <option value="real_estate">Real estate</option>
                <option value="support">Customer support</option>
              </select>
            </label>
            <label className="block text-sm">
              Agent name
              <input
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Purpose
              <textarea
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                rows={3}
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              />
            </label>
          </>
        )}

        {step === 1 && (
          <div className="space-y-3">
            {Object.entries(caps).map(([key, value]) => (
              <label key={key} className="flex items-center gap-3 text-sm capitalize">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => setCaps({ ...caps, [key]: e.target.checked })}
                />
                {key.replaceAll("_", " ")}
              </label>
            ))}
          </div>
        )}

        {step === 2 && (
          <>
            <fieldset className="text-sm">
              <legend className="mb-2">Personality</legend>
              {["professional", "friendly", "casual"].map((p) => (
                <label key={p} className="mr-4 inline-flex items-center gap-2 capitalize">
                  <input
                    type="radio"
                    name="personality"
                    checked={personality === p}
                    onChange={() => setPersonality(p)}
                  />
                  {p}
                </label>
              ))}
            </fieldset>
            <label className="block text-sm">
              Voice
              <select
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                value={voice}
                onChange={(e) => setVoice(e.target.value)}
              >
                <option value="alloy">Alloy</option>
                <option value="ash">Ash</option>
                <option value="ballad">Ballad</option>
                <option value="coral">Coral</option>
                <option value="echo">Echo</option>
                <option value="sage">Sage</option>
                <option value="shimmer">Shimmer</option>
                <option value="verse">Verse</option>
              </select>
            </label>
            <label className="block text-sm">
              Greeting
              <textarea
                className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
                rows={3}
                value={greeting}
                onChange={(e) => setGreeting(e.target.value)}
              />
            </label>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-between pt-2">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep(Math.max(0, step - 1))}
            className="text-sm text-[var(--muted)] disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-[var(--ink)] px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            {step < 2 ? "Continue" : loading ? "Creating…" : "Create agent"}
          </button>
        </div>
      </form>
    </DashboardShell>
  );
}
