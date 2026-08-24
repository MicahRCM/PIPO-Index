import type { Metadata } from "next";
import CasTool from "@/components/cas/CasTool";
import { HowTo, HowToPill, Step } from "@/components/HowTo";

export const metadata: Metadata = {
  title: "Cost After Scholarship · PIPO Index",
  description:
    "Net price of schools by family-income band, after need- and merit-based aid.",
};

export default function CasPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="reveal border-b border-rule pb-7">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          CAS · The net-price ledger
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Cost After Scholarship
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink-soft">
          What schools actually cost once need- and merit-based aid is applied,
          broken out by family income. Filter by classification, search, sort any
          income band, and page through all schools.
        </p>
        <HowToPill />
      </header>
      <div className="mt-8">
        <CasTool />
      </div>

      <HowTo title="Reading Cost After Scholarship">
        <Step n={1} title="Read across the income bands">
          Each band column is the average net price a family in that income range
          actually pays after need- and merit-based grants and scholarships — not
          the sticker price.
        </Step>
        <Step n={2} title="Understand the Average column">
          The Average is the officially reported, enrollment-weighted average net
          price (the figure College Navigator shows) — it weights each band by how
          many students fall in it, so it is not the simple average of the five
          bands.
        </Step>
        <Step n={3} title="Filter and sort">
          Narrow by classification, public/private, region, state, or US News
          rank, then click any band header to rank schools by cost for that
          income level.
        </Step>
        <Step n={4} title="Open a school">
          Click a school&apos;s name to open its College Navigator page in a new
          tab.
        </Step>
      </HowTo>
    </div>
  );
}
