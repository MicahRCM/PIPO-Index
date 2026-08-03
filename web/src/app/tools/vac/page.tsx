import type { Metadata } from "next";
import VacTool from "@/components/vac/VacTool";

export const metadata: Metadata = {
  title: "Value-Added & Cost · PIPO Index",
  description:
    "Scatter of value-added performance vs. net price, by family-income band.",
};

export default function VacPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="reveal border-b border-rule pb-7">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          VAC · The value-for-money field
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Value-Added &amp; Cost
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink-soft">
          Each school plotted by the net price it charges a chosen family-income
          band (x) against its value-added score (y), colored by classification and
          control. Switch income bands, filter the field, then search the list to
          highlight a school&apos;s point.
        </p>
      </header>
      <div className="mt-8">
        <VacTool />
      </div>
    </div>
  );
}
