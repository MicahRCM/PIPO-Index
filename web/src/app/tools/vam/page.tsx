import type { Metadata } from "next";
import VamTool from "@/components/vam/VamTool";

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
      </header>
      <div className="mt-8">
        <VamTool />
      </div>
    </div>
  );
}
