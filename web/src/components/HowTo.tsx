import type { ReactNode } from "react";

/**
 * Recipe-site-style "jump to instructions" affordance. `HowToPill` sits in a
 * tool's header and smooth-scrolls (via a plain #anchor — see the
 * `scroll-behavior: smooth` rule in globals.css) down to `HowTo`, the
 * instructions section rendered beneath the tool. Both share the `#how-to-use`
 * anchor; `scroll-mt` keeps the heading clear of the top of the viewport.
 */
export function HowToPill() {
  return (
    <a
      href="#how-to-use"
      className="group mt-4 inline-flex items-center gap-2 rounded-full border border-rule bg-panel px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft transition-colors hover:border-teal hover:text-teal"
    >
      How to use this tool
      <span aria-hidden className="transition-transform group-hover:translate-y-0.5 motion-safe:animate-bounce">
        ↓
      </span>
    </a>
  );
}

/** Numbered step — pass several as `HowTo` children. */
export function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="flex gap-3.5">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-rule bg-panel font-mono text-[11px] text-teal">
        {n}
      </span>
      <div className="min-w-0">
        <p className="font-display text-[15px] font-semibold text-ink">{title}</p>
        <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">{children}</p>
      </div>
    </li>
  );
}

export function HowTo({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      id="how-to-use"
      className="reveal mt-16 scroll-mt-24 border-t border-rule pt-10"
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
        How to use
      </p>
      <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        {title}
      </h2>
      <ol className="mt-6 max-w-2xl space-y-5">{children}</ol>
    </section>
  );
}
