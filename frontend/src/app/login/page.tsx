"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, setToken } from "@/lib/api";

function looksLikeEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("+91");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!looksLikeEmail(email)) {
      setError("Enter a valid email address (example@gmail.com).");
      setLoading(false);
      return;
    }
    if (mode === "signup" && phone.replace(/\D/g, "").length < 10) {
      setError("Enter a valid phone with country code, e.g. +918318762518");
      setLoading(false);
      return;
    }

    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const body =
        mode === "login"
          ? { email: email.trim().toLowerCase(), password }
          : {
              email: email.trim().toLowerCase(),
              phone: phone.trim(),
              password,
              name: name.trim(),
            };
      const res = await api<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[var(--bg)] px-5">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(31,138,122,0.18),_transparent_50%)]" />
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-8 backdrop-blur">
        <Link href="/" className="font-[family-name:var(--font-display)] text-2xl">
          Vela<span className="text-[var(--accent)]">Voice</span>
        </Link>
        <h1 className="mt-6 text-xl font-medium">
          {mode === "login" ? "Sign in to your workspace" : "Create your account"}
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Valid email required. Each email and phone can register only once.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {mode === "signup" && (
            <label className="block text-sm">
              Full name
              <input
                className="mt-1 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                minLength={2}
              />
            </label>
          )}
          <label className="block text-sm">
            Email
            <input
              type="email"
              autoComplete="email"
              className="mt-1 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </label>
          {mode === "signup" && (
            <label className="block text-sm">
              Phone (with country code)
              <input
                type="tel"
                className="mt-1 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+918318762518"
                required
              />
            </label>
          )}
          <label className="block text-sm">
            Password
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="mt-1 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-[var(--ink)] py-2.5 text-sm font-medium text-white disabled:opacity-60"
          >
            {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button
          type="button"
          className="mt-4 text-sm text-[var(--muted)] hover:text-[var(--ink)]"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login");
            setError("");
          }}
        >
          {mode === "login"
            ? "Need an account? Sign up"
            : "Already registered? Sign in"}
        </button>
      </div>
    </div>
  );
}
