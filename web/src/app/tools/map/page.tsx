import type { Metadata } from "next";
import MapTool from "@/components/map/MapTool";
import { HowTo, HowToPill, Step } from "@/components/HowTo";

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
        <HowToPill />
      </header>
      <div className="mt-8">
        <MapTool />
      </div>

      <HowTo title="Reading the Atlas Map">
        <Step n={1} title="Choose what the color means">
          The &ldquo;Color by&rdquo; menu recolors every dot by the indicator you
          pick — value-added, outcomes, selectivity, cost, or student
          composition.
        </Step>
        <Step n={2} title="Read the legend">
          The color ramp maps hue to value. For value-added measures the scale is
          diverging and centered on the median, so warm and cool read as
          above/below typical.
        </Step>
        <Step n={3} title="Hover and pin dots">
          Hover a dot to see its name and value. Click it to pin (its name links
          to College Navigator); hover another dot to compare two at once.
        </Step>
        <Step n={4} title="Zoom and pan">
          Scroll or use +/− to zoom, drag to pan, and ⟳ to reset. Filter by
          classification, public/private, region, state, or rank on the left.
        </Step>
      </HowTo>
    </div>
  );
}
