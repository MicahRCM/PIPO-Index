import { stateName } from "./states";
import type { FilterDef, FilterState } from "./filters";
import type { Institution } from "./types";

/**
 * Region ↔ State helpers shared by every tool's FilterPanel.
 *
 * The Region and State filters used to fight each other: you could pick a state
 * outside the chosen region (→ zero points), and nothing told you which states
 * belonged to which region. These helpers make State depend on Region — the
 * State dropdown is grouped by region and, once a Region is chosen, narrows to
 * just that region's states — and `pruneStatesToRegion` drops any selected
 * state that falls outside a newly-chosen region.
 *
 * A state can belong to more than one region (e.g. NY is both "Mid East" and
 * "Service Schools"), so the state→region map holds a set.
 */
export interface RegionIndex {
  regions: string[];
  statesByRegion: Map<string, { label: string; value: string }[]>;
  regionsForState: Map<string, Set<string>>;
}

export function buildRegionIndex(institutions: Institution[] | null): RegionIndex {
  const regions = new Set<string>();
  const codesByRegion = new Map<string, Set<string>>();
  const regionsForState = new Map<string, Set<string>>();
  institutions?.forEach((i) => {
    if (!i.region) return;
    regions.add(i.region);
    if (!i.state) return;
    if (!codesByRegion.has(i.region)) codesByRegion.set(i.region, new Set());
    codesByRegion.get(i.region)!.add(i.state);
    if (!regionsForState.has(i.state)) regionsForState.set(i.state, new Set());
    regionsForState.get(i.state)!.add(i.region);
  });
  const statesByRegion = new Map<string, { label: string; value: string }[]>();
  for (const [region, codes] of codesByRegion) {
    statesByRegion.set(
      region,
      [...codes]
        .map((c) => ({ label: stateName(c), value: c }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    );
  }
  return { regions: [...regions].sort(), statesByRegion, regionsForState };
}

/** Region single-select FilterDef. */
export function regionDef(idx: RegionIndex): FilterDef {
  return {
    kind: "select",
    id: "region",
    label: "Region",
    field: "region",
    options: idx.regions.map((r) => ({ label: r, value: r })),
  };
}

/**
 * State multi-select FilterDef, grouped by region. When a region is selected,
 * only that region's states are offered (so you can't pick a state that would
 * empty the plot); otherwise every region-group is shown so the groupings are
 * always visible.
 */
export function stateDef(idx: RegionIndex, selectedRegion?: string | null): FilterDef {
  const regionList = selectedRegion && idx.statesByRegion.has(selectedRegion)
    ? [selectedRegion]
    : idx.regions;
  const groups = regionList
    .filter((r) => idx.statesByRegion.has(r))
    .map((r) => ({ label: r, options: idx.statesByRegion.get(r)! }));
  return {
    kind: "select",
    id: "state",
    label: "State",
    field: "state",
    multi: true,
    options: groups.flatMap((g) => g.options),
    optionGroups: groups,
  };
}

/** Drop selected states that fall outside a chosen region (prevents empty plots). */
export function pruneStatesToRegion(next: FilterState, idx: RegionIndex): FilterState {
  const region = next.region;
  const states = next.state;
  if (typeof region !== "string" || !region || !Array.isArray(states)) return next;
  const codes = states.filter((s): s is string => typeof s === "string");
  const kept = codes.filter((s) => idx.regionsForState.get(s)?.has(region));
  if (kept.length === codes.length) return next;
  return { ...next, state: kept.length ? kept : undefined };
}
