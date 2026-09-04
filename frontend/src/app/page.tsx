import Link from "next/link";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#07151c] text-[#eef6f4]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(31,138,122,0.35),transparent_35%),radial-gradient(circle_at_80%_10%,rgba(217,119,69,0.18),transparent_28%),linear-gradient(160deg,#07151c_0%,#0b1f2a_55%,#12333d_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-1/2 bg-[url('data:image/svg+xml,%3Csvg width=%2760%27 height=%2760%27 viewBox=%270 0 60 60%27 xmlns=%27http://www.w3.org/2000/svg%27%3E%3Cg fill=%27none%27 fill-rule=%27evenodd%27%3E%3Cg fill=%27%23ffffff%27 fill-opacity=%270.03%27%3E%3Cpath d=%27M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z%27/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')] opacity-60" />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          Vela<span className="text-[#5fd0bf]">Voice</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Link href="/login" className="text-white/70 transition hover:text-white">
            Sign in
          </Link>
          <Link
            href="/login"
            className="rounded-md bg-[#1f8a7a] px-4 py-2 font-medium text-white transition hover:brightness-110"
          >
            Create your agent
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto grid max-w-6xl items-center gap-12 px-6 pb-24 pt-10 md:grid-cols-[1.1fr_0.9fr] md:pt-16">
        <section className="animate-rise">
          <p className="mb-4 font-[family-name:var(--font-display)] text-5xl leading-[1.05] tracking-tight md:text-7xl">
            VelaVoice
          </p>
          <h1 className="max-w-xl text-xl text-white/80 md:text-2xl">
            Build your AI voice agent for your business.
          </h1>
          <p className="mt-4 max-w-lg text-base text-white/55">
            Answer calls. Handle questions. Book appointments. Capture leads — with realtime
            voice, business knowledge, and tools that actually take action.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/login"
              className="rounded-md bg-white px-5 py-3 text-sm font-semibold text-[#0b1f2a] transition hover:bg-[#dff7f2]"
            >
              Create your agent
            </Link>
            <a
              href="#how"
              className="rounded-md border border-white/20 px-5 py-3 text-sm text-white/80 transition hover:border-white/40"
            >
              See how it works
            </a>
          </div>
        </section>

        <section className="animate-float relative mx-auto flex h-[360px] w-full max-w-md items-center justify-center">
          <div className="pulse-ring relative flex h-56 w-56 items-center justify-center rounded-full bg-[radial-gradient(circle,_rgba(95,208,191,0.25),_transparent_70%)]">
            <div className="flex h-40 w-40 flex-col items-center justify-center rounded-full border border-white/15 bg-white/5 backdrop-blur-md">
              <span className="text-xs uppercase tracking-[0.2em] text-white/50">Live call</span>
              <span className="mt-2 font-[family-name:var(--font-display)] text-3xl text-[#9ef0e2]">
                Sarah
              </span>
              <span className="mt-1 text-sm text-white/60">ABC Dental Clinic</span>
            </div>
          </div>
        </section>
      </main>

      <section id="how" className="relative z-10 border-t border-white/10 bg-black/20 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-[family-name:var(--font-display)] text-3xl">How it works</h2>
          <p className="mt-2 max-w-xl text-white/55">
            Four steps from empty account to a phone number that books appointments.
          </p>
          <ol className="mt-10 grid gap-8 md:grid-cols-4">
            {[
              ["01", "Create your agent", "Name, personality, greeting, and capabilities."],
              ["02", "Add business knowledge", "Upload PDFs, FAQs, website, and policies."],
              ["03", "Connect your phone number", "Twilio inbound number streams into realtime AI."],
              ["04", "Let AI handle calls", "Tools book appointments, capture leads, escalate."],
            ].map(([n, title, body]) => (
              <li key={n} className="animate-rise">
                <div className="text-sm text-[#5fd0bf]">{n}</div>
                <h3 className="mt-2 text-lg font-medium">{title}</h3>
                <p className="mt-2 text-sm text-white/50">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  );
}
