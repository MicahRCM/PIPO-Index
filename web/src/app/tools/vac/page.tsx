import type { Metadata } from "next";
import VacTool from "@/components/vac/VacTool";
import { HowTo, HowToPill, Step } from "@/components/HowTo";

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
        <HowToPill />
      </header>
      <div className="mt-8">
        <VacTool />
      </div>

      <HowTo title="Reading Value-Added & Cost">
        <Step n={1} title="Read the axes">
          The horizontal axis is net price (what students actually pay) and the
          vertical axis is the value-added score. The lower-right is the sweet
          spot: high value added at low cost.
        </Step>
        <Step n={2} title="Switch the income band">
          The band selector changes the cost axis to the net price for a chosen
          family-income range. &ldquo;Average&rdquo; shows the overall average net
          price across all bands.
        </Step>
        <Step n={3} title="Filter the field">
          Narrow by classification, public/private, region, state, or US News
          rank. Choosing a region limits the state list to that region.
        </Step>
        <Step n={4} title="Highlight and pin schools">
          Search or hover a name in the list to flag its dot. Click a dot to pin
          it; click the pinned name to open its College Navigator page. Hover
          another dot to compare two at once.
        </Step>
        <Step n={5} title="Zoom in on a cluster">
          Scroll or use +/− to zoom and drag to pan; Reset returns to the full
          field.
        </Step>
      </HowTo>
    </div>
  );
}
