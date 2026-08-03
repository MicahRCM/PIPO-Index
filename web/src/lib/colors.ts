/**
 * Categorical palette — "The Privilege Atlas" editorial series.
 * The first six mirror the --color-series-1..6 tokens in globals.css
 * (teal, ochre, oxblood, slate-blue, olive, plum); the remainder are
 * harmonious warm-almanac extensions so a larger set of selected schools
 * still reads as one coherent family.
 */
export const PALETTE = [
  "#0c6b61", // series-1 · teal
  "#d99016", // series-2 · ochre
  "#9b3a2e", // series-3 · oxblood
  "#3b5b78", // series-4 · slate-blue
  "#6b6233", // series-5 · olive
  "#7a4a6b", // series-6 · plum
  "#15897b", // teal-bright
  "#b87d18", // deep ochre
  "#a8553f", // brick
  "#52708a", // dusty blue
  "#857c46", // moss
  "#9a6a86", // mauve
];

/**
 * Deterministic color for a key (e.g. a unitid). Same key always maps to the
 * same color regardless of selection order, so a school keeps its color across
 * sessions and across tools. Uses a simple stable string hash into PALETTE.
 */
export function stableColor(key: string | number): string {
  const s = String(key);
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) | 0;
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}
