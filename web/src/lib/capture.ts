/**
 * TEMP — book-figure capture tool. Lets an author force all chart cards into a
 * chosen greyscale look (live, site-wide, persisted) and export any card as a
 * high-res PNG. Hidden behind a typed unlock ("grey"); invisible to normal
 * visitors. Safe to delete wholesale after the book figures are shot:
 *   - this file
 *   - src/components/CaptureMenu.tsx, src/components/CaptureButton.tsx
 *   - the "CAPTURE MODE" block in globals.css
 *   - the <CaptureMenu/> mount in layout.tsx
 *   - the data-capture / ref / <CaptureButton/> lines in Chart.tsx + MapTool.tsx
 */

export const MODE_KEY = "pipo-capture-grey";
export const ARMED_KEY = "pipo-capture-armed";

/** The word the author types anywhere to reveal the capture menu. */
export const UNLOCK_WORD = "grey";

export type GreyMode = "off" | "mono" | "soft" | "ink" | "noir";

/**
 * Menu options. The actual `filter` values live in globals.css keyed by
 * `html[data-grey="…"]` so the on-screen preview and the exported PNG share one
 * source of truth (html-to-image copies the card's computed filter).
 */
export const MODES: { id: GreyMode; label: string; hint: string }[] = [
  { id: "off", label: "Color", hint: "original palette" },
  { id: "mono", label: "Mono", hint: "flat luminance grey" },
  { id: "soft", label: "Soft", hint: "lighter, gentle contrast" },
  { id: "ink", label: "Ink", hint: "punchy print grey" },
  { id: "noir", label: "Noir", hint: "very high contrast" },
];

export function isGreyMode(v: string | null): v is GreyMode {
  return v === "off" || v === "mono" || v === "soft" || v === "ink" || v === "noir";
}

function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "chart"
  );
}

/**
 * Rasterize a chart card to a PNG and trigger a download. Uses html-to-image so
 * the whole card (HTML header/legend + the Recharts/map SVG) is captured, at
 * 3x for print. The export button and anything tagged data-export-ignore is
 * dropped from the capture.
 */
export async function exportCard(node: HTMLElement, name: string): Promise<void> {
  const { toPng } = await import("html-to-image");
  const bg = getComputedStyle(node).backgroundColor || "#fbf7ee";
  const dataUrl = await toPng(node, {
    pixelRatio: 3,
    cacheBust: true,
    backgroundColor: bg,
    filter: (el) =>
      !(el instanceof HTMLElement && el.dataset.exportIgnore !== undefined),
  });
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = `${slugify(name)}-${stamp}.png`;
  a.click();
}
