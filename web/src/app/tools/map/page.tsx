import type { Metadata } from "next";
import MapTool from "@/components/map/MapTool";

export const metadata: Metadata = {
  title: "The Atlas Map · PIPO Index",
  description: "Every institution on a US map, colored by any indicator.",
};

export default function MapPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="reveal border-b border-rule pb-7">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          MAP · The institutional atlas
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          The Atlas Map
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink-soft">
          Every institution plotted by its location, each dot colored by the
          indicator you choose — value-added, outcomes, selectivity, cost, or
          composition. Filter the field, then read the country as a single field
          of privilege in and privilege out.
        </p>
      </header>
      <div className="mt-8">
        <MapTool />
      </div>
    </div>
  );
}
