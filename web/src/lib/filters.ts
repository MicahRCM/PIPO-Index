import type { Institution, MetricValue } from "./types";

/**
 * Declarative filter configuration — replaces the legacy magic-number onclick
 * filters. A tool describes its filters as data (FilterDef[]); the FilterPanel
 * component renders controls and produces a FilterState; `applyFilters` runs
 * them. No filter logic is hard-coded into components or tied to numeric ids.
 */

export type FilterDef =
  | {
      kind: "select";
      id: string;
      label: string;
      /** Variable id in Institution.metrics, or "state" / "region". */
      field: string;
      /** `value` may be a boolean/number for flag/numeric fields; applyFilters
       * and the panel coerce to string, so a National flag option works. */
      options: { label: string; value: string | number | boolean }[];
      /**
       * When true the panel omits the "All" choice, forcing one option to be
       * selected. Used where combining the groups would be invalid — e.g. the
       * VAI ranking, where National and Other 4-Year are scored by different
       * models and cannot be ranked in a single list.
       */
      required?: boolean;
      /**
       * When true, several options can be chosen at once; the FilterState value
       * is a `string[]` and a row passes if its field matches ANY selected
       * option. Used for the State filter (browse a handful of states together).
       */
      multi?: boolean;
      /**
       * Optional grouped presentation for a `multi` select (e.g. States grouped
       * by Region). The panel renders headers per group; `options` should still
       * carry the flat union for filtering/fallback.
       */
      optionGroups?: { label: string; options: { label: string; value: string }[] }[];
    }
  | {
      kind: "range";
      id: string;
      label: string;
      field: string;
      min: number;
      max: number;
      step?: number;
    }
  | {
      kind: "toggle";
      id: string;
      label: string;
      field: string;
      /** Row passes when field strictly equals this value. */
      equals: MetricValue;
    };

/** Current value for each filter, keyed by FilterDef.id. */
export type FilterState = Record<
  string,
  string | number | [number, number] | string[] | boolean | undefined
>;

function fieldValue(inst: Institution, field: string): MetricValue {
  if (field === "state") return inst.state;
  if (field === "region") return inst.region;
  if (field === "name") return inst.name;
  return inst.metrics[field] ?? null;
}

/** Apply a declarative filter set to a list of institutions. */
export function applyFilters(
  rows: Institution[],
  defs: FilterDef[],
  state: FilterState,
): Institution[] {
  return rows.filter((row) =>
    defs.every((def) => {
      const v = state[def.id];
      if (v === undefined || v === "" || v === null) return true; // unset = no-op
      if (Array.isArray(v) && def.kind === "select" && v.length === 0) return true;
      const fv = fieldValue(row, def.field);

      switch (def.kind) {
        case "select":
          // Multi-select: pass if the field matches ANY chosen option.
          if (Array.isArray(v)) return v.map(String).includes(String(fv));
          // Coerce both sides: HTML <select> values arrive as strings, so a
          // boolean/numeric field (e.g. a National flag) still matches its
          // option. String matches (state/region/control) are unaffected.
          return String(fv) === String(v);
        case "toggle":
          return v === true ? fv === def.equals : true;
        case "range": {
          const [lo, hi] = v as [number, number];
          if (typeof fv !== "number") return false;
          return fv >= lo && fv <= hi;
        }
      }
    }),
  );
}
