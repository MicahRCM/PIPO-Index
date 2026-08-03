import type { VariableDef } from "./types";

/**
 * Registry of analytical variables.
 *
 * This is the single place that knows what variables exist and how to present
 * them. Tables, filters, and chart axes are driven off these defs by id, so
 * swapping in the richer merged dataset is mostly a matter of extending this
 * list (and the loader mapping in ./data.ts) — components don't change.
 */
export const VARIABLES = {
  vaRetention: {
    id: "vaRetention",
    label: "Value-Added Retention",
    kind: "number",
    description: "Retention performance relative to expectation (percentage points).",
  },
  vaGraduation: {
    id: "vaGraduation",
    label: "Value-Added Graduation",
    kind: "number",
    description: "Graduation performance relative to expectation (percentage points).",
  },
  vaDistance: {
    id: "vaDistance",
    label: "Value-Added",
    kind: "number",
    description: "Composite value-added score combining value-added retention and graduation.",
  },
  retentionRate: {
    id: "retentionRate",
    label: "Retention Rate",
    kind: "percent",
    unit: "%",
    description: "First-to-second-year full-time retention rate.",
  },
  graduationRate: {
    id: "graduationRate",
    label: "Graduation Rate",
    kind: "percent",
    unit: "%",
    description: "Six-year graduation rate.",
  },
  usNewsRank: {
    id: "usNewsRank",
    label: "US News Rank within Category",
    kind: "rank",
    description: "US News & World Report rank within category.",
  },
  nationalUniversity: {
    id: "nationalUniversity",
    label: "National University",
    kind: "flag",
    description: "Whether the institution is classified as a National University.",
  },
  publicPrivate: {
    id: "publicPrivate",
    label: "Public / Private",
    kind: "category",
    description: "Public vs. private control.",
  },

  // --- Merged dataset: canonical analytical variables -----------------------
  // Snapshot = latest available (most recent non-null) year per variable.
  // Native scale: rates/shares are fractions 0-1, prices/debt are dollars,
  // SAT/ACT are scores. Ids match the institutions_master.csv column names.
  retention_ft: {
    id: "retention_ft",
    label: "Retention Rate (Full-Time)",
    kind: "percent",
    unit: "%",
    description: "First-to-second-year full-time retention rate (fraction 0-1).",
  },
  grad_rate_6yr: {
    id: "grad_rate_6yr",
    label: "6-Year Graduation Rate",
    kind: "percent",
    unit: "%",
    description: "Six-year graduation rate (fraction 0-1).",
  },
  grad_rate_6yr_pell: {
    id: "grad_rate_6yr_pell",
    label: "6-Year Graduation Rate (Pell)",
    kind: "percent",
    unit: "%",
    description: "Six-year graduation rate for Pell recipients (fraction 0-1).",
  },
  grad_rate_6yr_nonpell: {
    id: "grad_rate_6yr_nonpell",
    label: "6-Year Graduation Rate (Non-Pell)",
    kind: "percent",
    unit: "%",
    description: "Six-year graduation rate for non-Pell students (fraction 0-1).",
  },
  pct_part_time: {
    id: "pct_part_time",
    label: "Part-Time Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates enrolled part-time (fraction 0-1).",
  },
  pct_pell: {
    id: "pct_pell",
    label: "Pell Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates receiving Pell grants (fraction 0-1).",
  },
  pct_international: {
    id: "pct_international",
    label: "International Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates who are international (fraction 0-1).",
  },
  pct_white: {
    id: "pct_white",
    label: "White Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates identifying as White (fraction 0-1).",
  },
  pct_black: {
    id: "pct_black",
    label: "Black Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates identifying as Black (fraction 0-1).",
  },
  pct_hispanic: {
    id: "pct_hispanic",
    label: "Hispanic Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates identifying as Hispanic (fraction 0-1).",
  },
  pct_asian: {
    id: "pct_asian",
    label: "Asian Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates identifying as Asian (fraction 0-1).",
  },
  pct_aian: {
    id: "pct_aian",
    label: "American Indian / Alaska Native Share",
    kind: "percent",
    unit: "%",
    description: "Share identifying as American Indian or Alaska Native (fraction 0-1).",
  },
  pct_nhpi: {
    id: "pct_nhpi",
    label: "Native Hawaiian / Pacific Islander Share",
    kind: "percent",
    unit: "%",
    description: "Share identifying as Native Hawaiian or Pacific Islander (fraction 0-1).",
  },
  pct_two_or_more: {
    id: "pct_two_or_more",
    label: "Two or More Races Share",
    kind: "percent",
    unit: "%",
    description: "Share identifying as two or more races (fraction 0-1).",
  },
  pct_unknown: {
    id: "pct_unknown",
    label: "Race Unknown Share",
    kind: "percent",
    unit: "%",
    description: "Share with race/ethnicity unknown (fraction 0-1).",
  },
  pct_minority: {
    id: "pct_minority",
    label: "Minority Share",
    kind: "percent",
    unit: "%",
    description: "Share of undergraduates identifying as a racial/ethnic minority (fraction 0-1).",
  },
  avg_net_price: {
    id: "avg_net_price",
    label: "Average Net Price",
    kind: "currency",
    unit: "$",
    description: "Average net price across all family-income bands.",
  },
  net_price_0_30k: {
    id: "net_price_0_30k",
    label: "Net Price ($0-30k Income)",
    kind: "currency",
    unit: "$",
    description: "Average net price for families with income $0-30k.",
  },
  net_price_30_48k: {
    id: "net_price_30_48k",
    label: "Net Price ($30-48k Income)",
    kind: "currency",
    unit: "$",
    description: "Average net price for families with income $30-48k.",
  },
  net_price_48_75k: {
    id: "net_price_48_75k",
    label: "Net Price ($48-75k Income)",
    kind: "currency",
    unit: "$",
    description: "Average net price for families with income $48-75k.",
  },
  net_price_75_110k: {
    id: "net_price_75_110k",
    label: "Net Price ($75-110k Income)",
    kind: "currency",
    unit: "$",
    description: "Average net price for families with income $75-110k.",
  },
  net_price_110k_plus: {
    id: "net_price_110k_plus",
    label: "Net Price ($110k+ Income)",
    kind: "currency",
    unit: "$",
    description: "Average net price for families with income above $110k.",
  },
  sat75_reading: {
    id: "sat75_reading",
    label: "SAT Reading (75th pctile)",
    kind: "number",
    description: "75th-percentile SAT Evidence-Based Reading & Writing score.",
  },
  sat75_math: {
    id: "sat75_math",
    label: "SAT Math (75th pctile)",
    kind: "number",
    description: "75th-percentile SAT Math score.",
  },
  sat75_writing: {
    id: "sat75_writing",
    label: "SAT Writing (75th pctile)",
    kind: "number",
    description: "75th-percentile SAT Writing score.",
  },
  act75_cumulative: {
    id: "act75_cumulative",
    label: "ACT Composite (75th pctile)",
    kind: "number",
    description: "75th-percentile ACT cumulative/composite score.",
  },
  act75_english: {
    id: "act75_english",
    label: "ACT English (75th pctile)",
    kind: "number",
    description: "75th-percentile ACT English score.",
  },
  act75_math: {
    id: "act75_math",
    label: "ACT Math (75th pctile)",
    kind: "number",
    description: "75th-percentile ACT Math score.",
  },
  act75_writing: {
    id: "act75_writing",
    label: "ACT Writing (75th pctile)",
    kind: "number",
    description: "75th-percentile ACT Writing score.",
  },
  acceptance_rate: {
    id: "acceptance_rate",
    label: "Acceptance Rate",
    kind: "percent",
    unit: "%",
    description: "Share of applicants admitted (fraction 0-1).",
  },
  median_debt: {
    id: "median_debt",
    label: "Median Debt",
    kind: "currency",
    unit: "$",
    description: "Median federal debt of completers at graduation.",
  },
  cost_attendance: {
    id: "cost_attendance",
    label: "Cost of Attendance",
    kind: "currency",
    unit: "$",
    description: "Total annual cost of attendance.",
  },
  tuition_in_state: {
    id: "tuition_in_state",
    label: "Tuition (In-State)",
    kind: "currency",
    unit: "$",
    description: "Published in-state tuition and fees.",
  },
  tuition_out_of_state: {
    id: "tuition_out_of_state",
    label: "Tuition (Out-of-State)",
    kind: "currency",
    unit: "$",
    description: "Published out-of-state tuition and fees.",
  },
  avg_net_price_public: {
    id: "avg_net_price_public",
    label: "Avg Net Price (Public)",
    kind: "currency",
    unit: "$",
    description: "Average net price reported by public institutions.",
  },
  avg_net_price_private: {
    id: "avg_net_price_private",
    label: "Avg Net Price (Private)",
    kind: "currency",
    unit: "$",
    description: "Average net price reported by private institutions.",
  },
  ug_size: {
    id: "ug_size",
    label: "Undergraduate Enrollment",
    kind: "number",
    description: "Total undergraduate enrollment (headcount).",
  },
} as const satisfies Record<string, VariableDef>;

/** Union of valid variable ids — gives autocomplete and compile-time safety. */
export type VariableId = keyof typeof VARIABLES;

export const VARIABLE_LIST: VariableDef[] = Object.values(VARIABLES);

export function getVariable(id: string): VariableDef | undefined {
  return (VARIABLES as Record<string, VariableDef>)[id];
}
