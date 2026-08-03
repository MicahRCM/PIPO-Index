"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TOOLS } from "@/lib/tools";

/**
 * Top navigation — the editorial masthead. Replaces legacy toolbar.html.
 * Each acronym carries a custom, instant-popping tooltip (CSS group-hover /
 * focus-within — no native `title` delay, no JS state).
 */
export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-paper/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-3.5">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex items-center" aria-hidden>
            <span className="dot-in transition-transform duration-500 group-hover:-translate-x-0.5" />
            <span className="dot-out transition-transform duration-500 group-hover:translate-x-0.5" />
          </span>
          <span className="font-display text-[1.35rem] font-semibold leading-none tracking-tight">
            PIPO
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft sm:inline">
            Index
          </span>
        </Link>

        <ul className="flex flex-wrap items-center gap-x-1 gap-y-1 font-mono text-[12px] uppercase tracking-[0.12em]">
          {TOOLS.map((tool) => {
            const live = tool.status === "live";
            const active = pathname === tool.href;
            return (
              <li key={tool.slug} className="group/tt relative">
                <Link
                  href={live ? tool.href : "#"}
                  aria-disabled={!live}
                  className={[
                    "relative block rounded-sm px-2.5 py-1.5 transition-colors",
                    !live
                      ? "cursor-not-allowed text-ink-soft/45"
                      : active
                        ? "text-teal"
                        : "text-ink-soft hover:text-ink",
                  ].join(" ")}
                >
                  {tool.code}
                  {active && (
                    <span className="absolute inset-x-2.5 -bottom-px h-0.5 bg-teal" />
                  )}
                </Link>

                {/* custom tooltip — instant, styled, accessible via focus-within */}
                <div
                  role="tooltip"
                  className="pointer-events-none absolute left-1/2 top-full z-40 mt-2 w-60 -translate-x-1/2 translate-y-1 scale-[0.98] opacity-0 transition-all duration-150 ease-out group-hover/tt:translate-y-0 group-hover/tt:scale-100 group-hover/tt:opacity-100 group-focus-within/tt:translate-y-0 group-focus-within/tt:scale-100 group-focus-within/tt:opacity-100"
                >
                  {/* caret */}
                  <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-l border-t border-rule bg-panel" />
                  <div className="relative overflow-hidden rounded-lg border border-rule bg-panel shadow-[0_12px_30px_-12px_rgba(27,36,48,0.35)]">
                    <div className="flex items-center justify-between border-b border-rule px-3.5 pb-2 pt-2.5">
                      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft">
                        {tool.code}
                      </span>
                      {live ? (
                        <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.16em] text-teal">
                          <span className="h-1 w-1 rounded-full bg-teal" />
                          Live
                        </span>
                      ) : (
                        <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-ochre">
                          Soon
                        </span>
                      )}
                    </div>
                    <div className="px-3.5 py-3">
                      <p className="font-display text-base font-medium leading-tight tracking-tight text-ink">
                        {tool.name}
                      </p>
                      <p className="mt-1.5 font-sans text-[12px] normal-case leading-snug tracking-normal text-ink-soft">
                        {tool.description}
                      </p>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
