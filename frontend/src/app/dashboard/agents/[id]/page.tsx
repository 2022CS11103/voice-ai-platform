"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import {
  Agent,
  DocumentItem,
  User,
  api,
  clearToken,
  formatDuration,
} from "@/lib/api";

type ChatMsg = { role: "user" | "assistant"; content: string };

function formatPhoneDisplay(phone: string) {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return phone;
}

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const agentId = Number(params.id);
  const [user, setUser] = useState<User | null>(null);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [textTitle, setTextTitle] = useState("Business information");
  const [textBody, setTextBody] = useState("");
  const [website, setWebsite] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const [chatHistory, setChatHistory] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [callMeNumber, setCallMeNumber] = useState("+918318762518");
  const [callMeStatus, setCallMeStatus] = useState("");
  const [callMeLoading, setCallMeLoading] = useState(false);

  async function reload() {
    const [me, ag, documents] = await Promise.all([
      api<User>("/api/auth/me"),
      api<Agent>(`/api/agents/${agentId}`),
      api<DocumentItem[]>(`/api/agents/${agentId}/documents`),
    ]);
    setUser(me);
    setAgent(ag);
    setDocs(documents);
  }

  useEffect(() => {
    reload().catch(() => {
      clearToken();
      router.replace("/login");
    });
  }, [agentId, router]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setError("");
    try {
      await api(`/api/agents/${agentId}/documents`, { method: "POST", body: form });
      setMessage(`Uploaded ${file.name}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function addText(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/api/agents/${agentId}/knowledge`, {
        method: "POST",
        body: JSON.stringify({ title: textTitle, content: textBody }),
      });
      setTextBody("");
      setMessage("Knowledge added");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function importSite(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/api/agents/${agentId}/knowledge/website`, {
        method: "POST",
        body: JSON.stringify({ url: website }),
      });
      setMessage("Website imported");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  }

  async function sendChat(e: FormEvent) {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    const text = chatInput.trim();
    setChatInput("");
    setChatLoading(true);
    setError("");
    try {
      const res = await api<{ reply: string; history: ChatMsg[] }>(
        `/api/agents/${agentId}/test`,
        {
          method: "POST",
          body: JSON.stringify({ message: text, history: chatHistory }),
        },
      );
      setChatHistory(res.history as ChatMsg[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test chat failed");
    } finally {
      setChatLoading(false);
    }
  }

  async function requestOutboundCall(e: FormEvent) {
    e.preventDefault();
    setCallMeStatus("");
    setError("");
    setCallMeLoading(true);
    try {
      const res = await api<{ message: string; to: string; call_sid: string }>(
        "/api/telephony/call-me",
        {
          method: "POST",
          body: JSON.stringify({ to: callMeNumber, agent_id: agentId }),
        },
      );
      setCallMeStatus(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Outbound call failed");
    } finally {
      setCallMeLoading(false);
    }
  }

  if (!agent) {
    return (
      <DashboardShell>
        <p className="text-[var(--muted)]">Loading agent…</p>
      </DashboardShell>
    );
  }

  const phone = agent.phone_number;
  const telHref = phone ? `tel:${phone.replace(/\s/g, "")}` : null;
  const bookingPath = `/book/${agent.business_id}`;

  return (
    <DashboardShell userName={user?.name}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl">{agent.name}</h1>
          <p className="mt-1 text-[var(--muted)]">{agent.business_name}</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700 capitalize">
          {agent.status}
        </span>
      </div>

      {/* CALL PANEL — this is the missing "call option" */}
      <section className="mt-8 rounded-2xl border border-[var(--accent)]/30 bg-gradient-to-br from-[#e7f6f3] to-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--accent)]">
              Live phone line
            </p>
            <p className="mt-2 font-[family-name:var(--font-display)] text-3xl">
              {phone ? formatPhoneDisplay(phone) : "Number not connected"}
            </p>
            <p className="mt-2 max-w-md text-sm text-[var(--muted)]">
              Do tarike: (1) system aapko call kare — neeche &quot;Call my phone&quot;,
              ya (2) aap Twilio number dial karo.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {telHref && (
              <a
                href={telHref}
                className="rounded-md border border-[var(--line)] bg-white px-4 py-3 text-sm"
              >
                Dial Twilio number
              </a>
            )}
            {phone && (
              <button
                type="button"
                className="rounded-md border border-[var(--line)] bg-white px-4 py-3 text-sm"
                onClick={async () => {
                  await navigator.clipboard.writeText(phone);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? "Copied!" : "Copy Twilio number"}
              </button>
            )}
            <Link
              href={bookingPath}
              className="rounded-md border border-[var(--line)] bg-white px-4 py-3 text-sm"
              target="_blank"
            >
              Open booking widget
            </Link>
          </div>
        </div>

        <form
          onSubmit={requestOutboundCall}
          className="mt-6 flex flex-wrap items-end gap-3 rounded-xl border border-[var(--line)] bg-white/80 p-4"
        >
          <label className="min-w-[220px] flex-1 text-sm">
            Call my phone (your number)
            <input
              className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={callMeNumber}
              onChange={(e) => setCallMeNumber(e.target.value)}
              placeholder="+918318762518"
              required
            />
          </label>
          <button
            type="submit"
            disabled={callMeLoading}
            className="rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {callMeLoading ? "Calling…" : "Call my phone"}
          </button>
        </form>
        {callMeStatus && (
          <p className="mt-3 text-sm text-emerald-700">{callMeStatus}</p>
        )}
        <p className="mt-3 text-xs text-[var(--muted)]">
          Twilio trial: pehle{" "}
          <a
            className="underline"
            href="https://console.twilio.com/us1/develop/phone-numbers/manage/verified"
            target="_blank"
            rel="noreferrer"
          >
            verify +918318762518
          </a>{" "}
          as a Verified Caller ID. Backend + ngrok running hona chahiye.
        </p>
        {!phone && (
          <p className="mt-4 text-sm text-amber-800">
            Set <code>TWILIO_PHONE_NUMBER</code> in backend <code>.env</code> and restart
            the API, then refresh this page.
          </p>
        )}
      </section>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-[var(--line)] bg-white/80 p-4">
          <div className="text-xs text-[var(--muted)]">Calls</div>
          <div className="mt-1 font-medium">
            {agent.call_count} · avg {formatDuration(agent.avg_duration_seconds)}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--line)] bg-white/80 p-4">
          <div className="text-xs text-[var(--muted)]">Voice / personality</div>
          <div className="mt-1 font-medium capitalize">
            {agent.voice} · {agent.personality}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--line)] bg-white/80 p-4">
          <div className="text-xs text-[var(--muted)]">Booking widget</div>
          <div className="mt-1 font-medium">
            <Link href={bookingPath} className="text-[var(--accent)] underline">
              /book/{agent.business_id}
            </Link>
          </div>
        </div>
      </div>

      {/* TEST AGENT — Elyra-style test without phone */}
      <section className="mt-10">
        <h2 className="text-xl font-medium">Test Agent</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Phone ke bina same brain + tools try karo (knowledge, availability, booking).
        </p>
        <div className="mt-4 overflow-hidden rounded-2xl border border-[var(--line)] bg-white/90">
          <div className="max-h-80 space-y-3 overflow-y-auto p-4">
            {chatHistory.length === 0 && (
              <p className="text-sm text-[var(--muted)]">
                Try: “What are your hours?” or “Book a table for 2 tomorrow at 7 PM”
              </p>
            )}
            {chatHistory.map((m, i) => (
              <div
                key={`${m.role}-${i}`}
                className={`rounded-xl px-3 py-2 text-sm ${
                  m.role === "assistant" ? "bg-[#e7f6f3]" : "border border-[var(--line)]"
                }`}
              >
                <div className="mb-1 text-[10px] uppercase tracking-wide text-[var(--muted)]">
                  {m.role === "assistant" ? agent.name : "You"}
                </div>
                {m.content}
              </div>
            ))}
            {chatLoading && (
              <p className="text-sm text-[var(--muted)]">{agent.name} is thinking…</p>
            )}
          </div>
          <form onSubmit={sendChat} className="flex gap-2 border-t border-[var(--line)] p-3">
            <input
              className="flex-1 rounded-md border border-[var(--line)] px-3 py-2 text-sm"
              placeholder="Type a message…"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
            />
            <button
              type="submit"
              disabled={chatLoading}
              className="rounded-md bg-[var(--ink)] px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-medium">Knowledge Base</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Upload PDFs/TXT/DOCX/CSV, import a website, or paste business info.
        </p>

        {(message || error) && (
          <p className={`mt-3 text-sm ${error ? "text-red-600" : "text-emerald-700"}`}>
            {error || message}
          </p>
        )}

        <div className="mt-4 overflow-hidden rounded-xl border border-[var(--line)] bg-white/80">
          <ul className="divide-y divide-[var(--line)]">
            {docs.length === 0 && (
              <li className="px-4 py-6 text-sm text-[var(--muted)]">No documents yet.</li>
            )}
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <div>
                  <div className="font-medium">{d.filename}</div>
                  <div className="text-[var(--muted)]">
                    {d.source_type} · {d.status}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <label className="rounded-xl border border-dashed border-[var(--line)] bg-white/60 p-4 text-sm">
            <div className="font-medium">Upload file</div>
            <input type="file" className="mt-3 block w-full text-xs" onChange={onUpload} />
          </label>

          <form
            onSubmit={importSite}
            className="rounded-xl border border-[var(--line)] bg-white/80 p-4 text-sm"
          >
            <div className="font-medium">Website</div>
            <input
              className="mt-3 w-full rounded-md border border-[var(--line)] px-3 py-2"
              placeholder="https://abcdental.com"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              required
            />
            <button
              type="submit"
              className="mt-3 rounded-md bg-[var(--ink)] px-3 py-1.5 text-white"
            >
              Import
            </button>
          </form>

          <form
            onSubmit={addText}
            className="rounded-xl border border-[var(--line)] bg-white/80 p-4 text-sm"
          >
            <div className="font-medium">Manual text</div>
            <input
              className="mt-3 w-full rounded-md border border-[var(--line)] px-3 py-2"
              value={textTitle}
              onChange={(e) => setTextTitle(e.target.value)}
            />
            <textarea
              className="mt-2 w-full rounded-md border border-[var(--line)] px-3 py-2"
              rows={4}
              value={textBody}
              onChange={(e) => setTextBody(e.target.value)}
              required
            />
            <button
              type="submit"
              className="mt-3 rounded-md bg-[var(--accent)] px-3 py-1.5 text-white"
            >
              Add knowledge
            </button>
          </form>
        </div>
      </section>

      <section className="mt-10 rounded-xl border border-[var(--line)] bg-white/80 p-5">
        <h2 className="text-lg font-medium">Greeting</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{agent.greeting}</p>
        <h2 className="mt-6 text-lg font-medium">Purpose</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{agent.purpose}</p>
      </section>
    </DashboardShell>
  );
}
