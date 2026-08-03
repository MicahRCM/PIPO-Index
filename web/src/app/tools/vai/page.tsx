import type { Metadata } from "next";
import VaiTool from "@/components/vai/VaiTool";

export const metadata: Metadata = {
  title: "Value-Added Index · PIPO Index",
  description:
    "Sortable ranking of value-added retention and graduation performance.",
};

export default function VaiPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="reveal border-b border-rule pb-7">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          VAI · The ranking ledger
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Value-Added Index
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink-soft">
          Schools ranked by value-added performance — how their retention and
          graduation outcomes compare to expectation. Filter by classification,
          search, sort any column, and page through all schools.
        </p>
      </header>
      <div className="mt-8">
        <VaiTool />
      </div>
    </div>
  );
}
