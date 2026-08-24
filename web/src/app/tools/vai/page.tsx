import type { Metadata } from "next";
import VaiTool from "@/components/vai/VaiTool";
import { HowTo, HowToPill, Step } from "@/components/HowTo";

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
        <HowToPill />
      </header>
      <div className="mt-8">
        <VaiTool />
      </div>

      <HowTo title="Reading the Value-Added Index">
        <Step n={1} title="Pick which ranking you're looking at">
          Classification is required: National Universities and Regional &amp;
          Liberal Arts are scored by different models, so each is ranked within
          its own group rather than in one combined list.
        </Step>
        <Step n={2} title="Read the columns">
          Rank is a school&apos;s standing among all its peers in that
          classification. The value-added retention and graduation columns are the
          scores behind the rank; graduation rate and US News rank are there for
          context.
        </Step>
        <Step n={3} title="Narrow without renumbering">
          Public/Private, Region, and State filter the view but keep each
          school&apos;s rank within its full group — so you&apos;ll see ranks like
          3, 7, 12… rather than a fresh 1, 2, 3.
        </Step>
        <Step n={4} title="Search and sort">
          Search by name, and click any column header to sort by it (click again
          to reverse).
        </Step>
        <Step n={5} title="Open a school">
          Click a school&apos;s name to open its College Navigator page in a new
          tab.
        </Step>
      </HowTo>
    </div>
  );
}
