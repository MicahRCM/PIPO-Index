"use client";

// TEMP — see src/lib/capture.ts. Hover-revealed PNG export button for a chart
// card. Rendered always, but hidden by CSS unless capture mode is armed
// (html[data-capture-on]) and the card is hovered.

import { useState, type RefObject } from "react";
import { exportCard } from "@/lib/capture";

export default function CaptureButton({
  targetRef,
  name,
}: {
  targetRef: RefObject<HTMLElement | null>;
  name: string;
}) {
  const [busy, setBusy] = useState(false);

  async function handle() {
    const node = targetRef.current;
    if (!node || busy) return;
    setBusy(true);
    try {
      await exportCard(node, name);
    } catch (err) {
      // Surface failures loudly rather than silently producing no file.
      console.error("[capture] export failed", err);
      alert("Export failed — see console for details.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handle}
      data-capture-btn
      data-export-ignore
      aria-label="Export this chart as a PNG image"
      className="absolute right-3 top-3 z-20 inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-paper shadow-sm transition hover:bg-teal disabled:opacity-60"
      disabled={busy}
    >
      {busy ? "Exporting…" : "Export PNG"}
      <span aria-hidden>↓</span>
    </button>
  );
}
