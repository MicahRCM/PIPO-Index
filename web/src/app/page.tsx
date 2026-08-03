import Link from "next/link";
import { TOOLS } from "@/lib/tools";
import HeroField from "@/components/HeroField";

// Kept deliberately to figures we can defend from the shipped dataset.
// (The previous band claimed 1,249 institutions / 22 continuous years /
// 33 indicators, none of which match the 2024 release.)
const FACTS = [
  { n: "1,004", l: "institutions" },
  { n: "2024", l: "entering cohort" },
  { n: "5", l: "family-income bands" },
  { n: "5", l: "tools" },
];

export default function Home() {
  return (
    <>
      {/* ── Masthead ─────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-rule">
        <div className="absolute inset-0 opacity-90">
          <HeroField />
        </div>
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-paper" />

        <div className="relative mx-auto w-full max-w-7xl px-6 pb-20 pt-20 sm:pt-28">
          <p
            className="reveal font-mono text-[11px] uppercase tracking-[0.34em] text-ink-soft"
            style={{ animationDelay: "0.05s" }}
          >
            An atlas of American higher education
          </p>

          <h1 className="mt-6 font-display text-6xl font-semibold leading-[0.92] tracking-tight sm:text-8xl">
            <span
              className="reveal block"
              style={{ animationDelay: "0.12s" }}
            >
              Privilege <span className="italic text-teal">in</span>,
            </span>
            <span
              className="reveal block"
              style={{ animationDelay: "0.24s" }}
            >
              privilege <span className="italic text-ochre">out</span>.
            </span>
          </h1>

          <p
            className="reveal mt-8 max-w-xl text-lg leading-relaxed text-ink-soft"
            style={{ animationDelay: "0.36s" }}
          >
            A college&rsquo;s headline numbers mostly measure who it admits — not
            what it does for them. PIPO separates the two, charting{" "}
            <span className="text-ink">retention, graduation, and true cost</span>{" "}
            against the privilege students bring in.
          </p>

          <div
            className="reveal mt-10 flex flex-wrap items-center gap-x-6 gap-y-3"
            style={{ animationDelay: "0.48s" }}
          >
            <Link
              href="/tools/vam"
              className="group inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 font-mono text-[12px] uppercase tracking-[0.16em] text-paper transition-colors hover:bg-teal"
            >
              Open the matrix
              <span className="transition-transform duration-300 group-hover:translate-x-1">
                &rarr;
              </span>
            </Link>
            <a
              href="#tools"
              className="link-underline font-mono text-[12px] uppercase tracking-[0.16em] text-ink-soft hover:text-ink"
            >
              Browse all tools
            </a>
          </div>
        </div>
      </section>

      {/* ── Facts band ───────────────────────────────────────── */}
      <section className="border-b border-rule bg-panel/60">
        <dl className="mx-auto grid max-w-7xl grid-cols-2 divide-rule sm:grid-cols-4 sm:divide-x">
          {FACTS.map((f, i) => (
            <div
              key={f.l}
              className="reveal-fade px-6 py-7"
              style={{ animationDelay: `${0.6 + i * 0.08}s` }}
            >
              <dt className="font-mono text-4xl tabular-nums tracking-tight text-ink">
                {f.n}
              </dt>
              <dd className="mt-1 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
                {f.l}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ── Tool index (ledger) ──────────────────────────────── */}
      <section id="tools" className="mx-auto w-full max-w-7xl px-6 py-20">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-3xl font-semibold tracking-tight">
            The tools
          </h2>
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-soft">
            {TOOLS.filter((t) => t.status === "live").length} live
          </span>
        </div>

        <ul className="mt-10 border-t border-rule">
          {TOOLS.map((tool, i) => {
            const live = tool.status === "live";
            const Row = (
              <div
                className={[
                  "group grid grid-cols-[auto_1fr_auto] items-center gap-5 border-b border-rule py-7 transition-colors sm:gap-8",
                  live ? "hover:bg-panel/70" : "opacity-55",
                ].join(" ")}
              >
                <span className="font-mono text-sm tabular-nums text-ink-soft">
                  {String(i + 1).padStart(2, "0")}
                </span>

                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <h3 className="font-display text-2xl font-medium tracking-tight transition-transform duration-300 group-hover:translate-x-1 sm:text-3xl">
                      {tool.name}
                    </h3>
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
                      {tool.code}
                    </span>
                  </div>
                  <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
                    {tool.description}
                  </p>
                </div>

                <div className="flex items-center gap-4 justify-self-end">
                  {live ? (
                    <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-teal">
                      <span className="h-1.5 w-1.5 rounded-full bg-teal" />
                      Live
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ochre">
                      Soon
                    </span>
                  )}
                  <span
                    className={[
                      "text-2xl transition-transform duration-300",
                      live
                        ? "text-ink group-hover:translate-x-1.5"
                        : "text-ink-soft/40",
                    ].join(" ")}
                    aria-hidden
                  >
                    &rarr;
                  </span>
                </div>
              </div>
            );

            return (
              <li key={tool.slug}>
                {live ? (
                  <Link href={tool.href} className="block">
                    {Row}
                  </Link>
                ) : (
                  <div>{Row}</div>
                )}
              </li>
            );
          })}
        </ul>

        <p className="mt-10 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Built on public data — IPEDS, the College Scorecard, and US News
          categories. Value-added figures compare each school&rsquo;s actual
          retention and graduation against what its incoming class predicts, so
          the credit goes to the <span className="text-ink">school</span> rather
          than to the privilege it admitted.
        </p>
      </section>
    </>
  );
}
