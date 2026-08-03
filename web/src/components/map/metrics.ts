import { VARIABLES, type VariableId } from "@/lib/variables";

/**
 * Curated set of map-able metrics, grouped for the variable selector.
 *
 * Only meaningful numeric metrics on a consistent native scale are offered
 * (the merged fractions/dollars/scores, the value-added residuals, and rank).
 * `diverging` flags residual metrics that should use the teal↔oxblood ramp
 * centered on the median; `reverse` flips the ramp so a lower raw value reads
 * as the "high" color (used for rank, where #1 is best).
 */
export interface MapMetric {
  id: VariableId;
  diverging?: boolean;
  reverse?: boolean;
}

export interface MapMetricGroup {
  label: string;
  metrics: MapMetric[];
}

export const MAP_METRIC_GROUPS: MapMetricGroup[] = [
  {
    label: "Value-Added",
    metrics: [
      { id: "vaDistance", diverging: true },
      { id: "vaRetention", diverging: true },
      { id: "vaGraduation", diverging: true },
    ],
  },
  {
    label: "Outcomes",
    metrics: [{ id: "grad_rate_6yr" }, { id: "retention_ft" }, { id: "acceptance_rate", reverse: true }],
  },
  {
    label: "Selectivity",
    metrics: [
      { id: "usNewsRank", reverse: true },
      { id: "sat75_math" },
      { id: "sat75_reading" },
      { id: "act75_cumulative" },
    ],
  },
  {
    label: "Cost & Debt",
    metrics: [
      { id: "net_price_0_30k" },
      { id: "net_price_30_48k" },
      { id: "net_price_48_75k" },
      { id: "net_price_75_110k" },
      { id: "net_price_110k_plus" },
      { id: "cost_attendance" },
      { id: "median_debt" },
      { id: "tuition_in_state" },
      { id: "tuition_out_of_state" },
    ],
  },
  {
    label: "Composition",
    metrics: [
      { id: "pct_pell" },
      { id: "pct_minority" },
      { id: "pct_international" },
      { id: "ug_size" },
    ],
  },
];

/** Flat lookup of every map metric by id. */
export const MAP_METRICS: Record<string, MapMetric> = Object.fromEntries(
  MAP_METRIC_GROUPS.flatMap((g) => g.metrics).map((m) => [m.id, m]),
);

/** Default metric shown on first load. */
export const DEFAULT_METRIC: VariableId = "vaDistance";

export function metricLabel(id: VariableId): string {
  return VARIABLES[id].label;
}
