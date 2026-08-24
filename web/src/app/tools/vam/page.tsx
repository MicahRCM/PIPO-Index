import type { Metadata } from "next";
import VamTool from "@/components/vam/VamTool";
import { HowTo, HowToPill, Step } from "@/components/HowTo";

export const metadata: Metadata = {
  title: "Value-Added Matrix · PIPO Index",
  description:
    "Scatter of value-added retention vs. graduation across all schools.",
};

export default function VamPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="reveal border-b border-rule pb-7">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          VAM · The value-added field
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Value-Added Matrix
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink-soft">
          Each school plotted by value-added graduation (x) and value-added
          retention (y), colored by classification and control. Filter the
          field, then search the list to highlight a school&apos;s point.
        </p>
        <HowToPill />
      </header>
      <div className="mt-8">
        <VamTool />
      </div>

      <HowTo title="Reading the Value-Added Matrix">
        <Step n={1} title="Read the axes as value added, not raw rates">
          The horizontal axis is value-added graduation and the vertical axis is
          value-added retention — how much better (positive) or worse (negative) a
          school does than its incoming students&apos; privilege would predict.
          The origin lines mark &ldquo;exactly as predicted.&rdquo;
        </Step>
        <Step n={2} title="Use the Value-Added Consistency line">
          The dashed diagonal is the typical balance between the two scores. A
          school above the line adds more value on retention than its graduation
          would predict; below it, the reverse.
        </Step>
        <Step n={3} title="Filter the field">
          Narrow by classification, public/private, region, state, or US News
          rank on the left. Choosing a region limits the state list to that
          region.
        </Step>
        <Step n={4} title="Highlight and pin schools">
          Search or hover a name in the right-hand list to flag its dot. Click a
          dot to pin it (it stays put); click the pinned name to open its College
          Navigator page. Hover another dot to compare two at once.
        </Step>
        <Step n={5} title="Zoom in on a cluster">
          Scroll or use +/− to zoom and drag to pan; Reset returns to the full
          field.
        </Step>
      </HowTo>
    </div>
  );
}
