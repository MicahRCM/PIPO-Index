import type { Metadata } from "next";
import CasTool from "@/components/cas/CasTool";

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
      </header>
      <div className="mt-8">
        <CasTool />
      </div>
    </div>
  );
}
