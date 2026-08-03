import type { VariableKind } from "@/lib/types";

/**
 * Color-scale + value-formatting helpers for the Atlas map.
 *
 * Two ramps, both drawn from the "Privilege Atlas" duotone:
 *   - sequential  teal → ochre   (most metrics; low → high)
 *   - diverging   teal ↔ oxblood (value-added / residual metrics; centered on
 *                                  the median so above/below expectation read
 *                                  as opposing hues)
 * Colors are interpolated in plain RGB — no d3-scale/-interpolate dependency,
 * so we keep full control of the exact stops and the client bundle stays lean.
 */

const TEAL = "#0c6b61";
const OCHRE = "#e0a53b";
const OXBLOOD = "#9b3a2e";
const NEUTRAL = "#cbb48f"; // muted tan midpoint for the diverging ramp

type RGB = [number, number, number];

function hexToRgb(hex: string): RGB {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function rgbToHex([r, g, b]: RGB): string {
  const c = (n: number) => Math.round(Math.max(0, Math.min(255, n))).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

function mix(a: RGB, b: RGB, t: number): RGB {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

const TEAL_RGB = hexToRgb(TEAL);
const OCHRE_RGB = hexToRgb(OCHRE);
const OXBLOOD_RGB = hexToRgb(OXBLOOD);
const NEUTRAL_RGB = hexToRgb(NEUTRAL);

/**
 * Sequential teal → ochre → oxblood, t in [0,1]. A three-stop ramp travels far
 * more hue than a straight teal→ochre blend, so low/high values are clearly
 * distinct (the previous two-stop ramp read as "green to yellow-green").
 */
export function sequentialColor(t: number): string {
  const u = clamp01(t);
  return rgbToHex(u < 0.5 ? mix(TEAL_RGB, OCHRE_RGB, u * 2) : mix(OCHRE_RGB, OXBLOOD_RGB, (u - 0.5) * 2));
}

/** Diverging teal ↔ oxblood through a neutral midpoint, t in [0,1] (0.5 = center). */
export function divergingColor(t: number): string {
  const u = clamp01(t);
  return rgbToHex(u < 0.5 ? mix(TEAL_RGB, NEUTRAL_RGB, u * 2) : mix(NEUTRAL_RGB, OXBLOOD_RGB, (u - 0.5) * 2));
}

function clamp01(t: number): number {
  return t < 0 ? 0 : t > 1 ? 1 : t;
}

/** Median of a numeric array (assumes non-empty). */
export function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Linear-interpolated percentile (p in [0,1]) of a numeric array. */
function percentile(sorted: number[], p: number): number {
  if (sorted.length === 1) return sorted[0];
  const i = p * (sorted.length - 1);
  const lo = Math.floor(i);
  const hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}

export interface ColorScale {
  /** Color for a raw metric value. */
  color: (value: number) => string;
  min: number;
  med: number;
  max: number;
  diverging: boolean;
}

/**
 * Build a color scale over the given values.
 *  - diverging metrics map min→teal, median→neutral, max→oxblood (piecewise so
 *    the median always lands on the neutral midpoint);
 *  - sequential metrics map min→teal, max→ochre.
 *  - `reverse` flips the ramp (used for rank, where #1 is "best").
 */
export function buildColorScale(values: number[], diverging: boolean, reverse: boolean): ColorScale {
  // Clamp the color domain to the 2nd–98th percentile so a few extreme
  // outliers (e.g. one 163k-enrollment school) don't compress everyone else
  // into a sliver of the ramp. Values past the clamp saturate at the endpoint
  // color; the legend shows these robust bounds. Diverging metrics stay
  // centered on the true median so 0 keeps its meaning.
  const sorted = [...values].sort((a, b) => a - b);
  const min = percentile(sorted, 0.02);
  const max = percentile(sorted, 0.98);
  const med = median(values);
  const ramp = diverging ? divergingColor : sequentialColor;

  function color(value: number): string {
    let t: number;
    if (diverging) {
      t =
        value <= med
          ? med === min
            ? 0.5
            : 0.5 * ((value - min) / (med - min))
          : max === med
            ? 0.5
            : 0.5 + 0.5 * ((value - med) / (max - med));
    } else {
      t = max === min ? 0.5 : (value - min) / (max - min);
    }
    return ramp(reverse ? 1 - t : t);
  }

  return { color, min, med, max, diverging };
}

/** Format a metric value for tooltips / legend ticks, by its registry kind. */
export function formatMetric(value: number, kind: VariableKind): string {
  switch (kind) {
    case "percent":
      // Merged shares/rates are fractions 0-1; render as whole-ish percents.
      return `${(value * 100).toFixed(value * 100 < 10 ? 1 : 0)}%`;
    case "currency":
      return `$${Math.round(value).toLocaleString()}`;
    case "rank":
      return `#${Math.round(value).toLocaleString()}`;
    case "number":
    default:
      return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
  }
}
