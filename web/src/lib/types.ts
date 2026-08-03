/**
 * Core data types for the PIPO-Index app.
 *
 * Design goal: the current dataset (1,249 institutions, a handful of
 * variables) must be swappable for the richer merged dataset (many more
 * variables, multiple years) WITHOUT rewriting components. We achieve that by
 * keeping a small set of always-present identity fields on `Institution` and
 * pushing every analytical variable into an open `metrics` bag keyed by a
 * stable variable id. Components read variables through the `VARIABLES`
 * registry (see ./variables.ts) rather than hard-coding field names, so adding
 * a variable is a registry edit, not a component rewrite.
 */

/** A metric value can be numeric, categorical, or missing. */
export type MetricValue = number | string | boolean | null;

/**
 * A single institution. Identity fields are guaranteed; everything analytical
 * lives in `metrics`, addressed by variable id (keys of VARIABLES).
 */
export interface Institution {
  /** IPEDS UNITID — the stable cross-dataset join key. */
  unitid: number;
  name: string;
  state: string | null;
  region: string | null;
  /** City from the IPEDS directory (for map tooltips); null if unknown. */
  city?: string | null;
  /** Point latitude from the IPEDS directory; null if the school has no directory row. */
  latitude?: number | null;
  /** Point longitude from the IPEDS directory; null if the school has no directory row. */
  longitude?: number | null;
  /** Open, extensible bag of analytical variables keyed by variable id. */
  metrics: Record<string, MetricValue>;
}

/** How a variable should be formatted/treated in UI. */
export type VariableKind = "number" | "percent" | "currency" | "rank" | "category" | "flag";

/** Declarative description of one analytical variable. */
export interface VariableDef {
  /** Stable id used as the key in Institution.metrics. */
  id: string;
  /** Human-readable label for tables, axes, legends. */
  label: string;
  kind: VariableKind;
  /** Optional unit suffix (e.g. "%"). */
  unit?: string;
  /** Optional longer description / tooltip. */
  description?: string;
}

/** Retention time-series for one institution. */
export interface RetentionInstitution {
  unitid: number;
  name: string;
  /** One value per year in RetentionSeries.years; null = missing. */
  rates: (number | null)[];
}

/** The full retention dataset: shared year axis + per-institution series. */
export interface RetentionSeries {
  years: number[];
  institutions: RetentionInstitution[];
}

/** Standard API envelope so clients get consistent metadata. */
export interface ApiResponse<T> {
  data: T;
  meta: {
    count: number;
    /** ISO timestamp the payload was generated. */
    generatedAt: string;
  };
}
