"use client";

import { useEffect, useMemo, useState } from "react";
import DataTable, { type Column } from "@/components/DataTable";
import CollegeNavLink from "@/components/CollegeNavLink";
import FilterPanel from "@/components/FilterPanel";
import { applyFilters, type FilterDef, type FilterState } from "@/lib/filters";
import { VARIABLES } from "@/lib/variables";
import { buildRegionIndex, regionDef, stateDef, pruneStatesToRegion } from "@/lib/regions";
import type { ApiResponse, Institution } from "@/lib/types";

/**
 * Value-Added Index — the legacy VAI ranking table, ported.
 *
 * Mirrors RetentionTool's shape: fetch the typed slice from /api, keep light
 * local state, and drive a reusable component (here DataTable). The legacy
 * National / Other-4-Year toggle becomes a declarative `select` FilterDef on
 * the `nationalUniversity` flag — no magic numbers, no hand-rolled filter code.
 *
 * Rank: the legacy app shipped a pre-computed "Value-Added Rank" per group. We
 * reproduce it by ranking the current (filtered) view on the composite
 * `vaDistance` score, descending, so the table opens as a ranking and each
 * group is ranked 1..N within itself — matching the legacy National/Other lists.
 */

interface VaiRow {
  inst: Institution;
  rank: number;
}

/**
 * Classification picks which ranking you are looking at. It is `required` (no
 * "All"): National and Other 4-Year are scored by different models, so a single
 * combined ranking would not be meaningful.
 */
const GROUP_FILTER: FilterDef[] = [
  {
    kind: "select",
    id: "national",
    label: "Classification",
    field: VARIABLES.nationalUniversity.id,
    required: true,
    options: [
      { label: "National Universities", value: true },
      { label: "Regional & Liberal Arts", value: false },
    ],
  },
];

/**
 * Applied AFTER ranking, so a school keeps its rank within its full
 * classification group rather than being renumbered 1..N inside the subset.
 */
const VIEW_FILTERS: FilterDef[] = [
  {
    kind: "select",
    id: "control",
    label: "Public / Private",
    field: VARIABLES.publicPrivate.id,
    // data.ts normalizes pubpriv to the strings "Public"/"Private", and
    // applyFilters compares String(fieldValue) === String(optionValue).
    options: [
      { label: "Public", value: "Public" },
      { label: "Private", value: "Private" },
    ],
  },
];

/** Default view: the National Universities ranking. */
const DEFAULT_FILTERS: FilterState = { national: "true" };

function fmtSigned(v: number | string | boolean | null): string {
  return typeof v === "number" ? v.toFixed(1) : "—";
}

function fmtPercent(v: number | string | boolean | null): string {
  return typeof v === "number" ? `${v.toFixed(1)}%` : "—";
}

export default function VaiTool() {
  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  useEffect(() => {
    let active = true;
    fetch("/api/institutions")
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<ApiResponse<Institution[]>>;
      })
      .then((res) => active && setInstitutions(res.data))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, []);

  // View filters (applied AFTER ranking): control + Region + State. Kept
  // separate from GROUP_FILTER so ranks hold when you narrow to e.g. a region or
  // a couple of states. State is grouped by (and gated to) the chosen Region.
  const regionIdx = useMemo(() => buildRegionIndex(institutions), [institutions]);
  const viewFilters = useMemo<FilterDef[]>(
    () => [
      ...VIEW_FILTERS,
      regionDef(regionIdx),
      stateDef(regionIdx, typeof filters.region === "string" ? filters.region : null),
    ],
    [regionIdx, filters.region],
  );
  const allFilters = useMemo<FilterDef[]>(() => [...GROUP_FILTER, ...viewFilters], [viewFilters]);

  const rows = useMemo<VaiRow[]>(() => {
    if (!institutions) return [];
    // 1. Rank across the WHOLE classification group, so ranks are the school's
    //    standing among all its peers...
    const group = applyFilters(institutions, GROUP_FILTER, filters);
    const ranked = [...group]
      .sort((a, b) => {
        const da = a.metrics[VARIABLES.vaDistance.id];
        const db = b.metrics[VARIABLES.vaDistance.id];
        return (typeof db === "number" ? db : -Infinity) - (typeof da === "number" ? da : -Infinity);
      })
      .map((inst, i) => ({ inst, rank: i + 1 }));

    // 2. ...then narrow the view. Ranks stay put (you'll see 3, 7, 12, …).
    const visible = new Set(applyFilters(group, viewFilters, filters));
    return ranked.filter((r) => visible.has(r.inst));
  }, [institutions, filters, viewFilters]);

  const columns = useMemo<Column<VaiRow>[]>(
    () => [
      {
        id: "rank",
        header: "Rank",
        accessor: (r) => r.rank,
        align: "right",
      },
      {
        id: "name",
        header: "Name",
        accessor: (r) => r.inst.name,
        render: (r) => <CollegeNavLink unitid={r.inst.unitid} name={r.inst.name} />,
        searchable: true,
      },
      {
        id: VARIABLES.vaRetention.id,
        header: "Value-Added\nRetention",
        accessor: (r) => r.inst.metrics[VARIABLES.vaRetention.id] as number | null,
        render: (r) => fmtSigned(r.inst.metrics[VARIABLES.vaRetention.id]),
        align: "right",
      },
      {
        id: VARIABLES.vaGraduation.id,
        header: "Value-Added\nGraduation",
        accessor: (r) => r.inst.metrics[VARIABLES.vaGraduation.id] as number | null,
        render: (r) => fmtSigned(r.inst.metrics[VARIABLES.vaGraduation.id]),
        align: "right",
      },
      {
        id: VARIABLES.graduationRate.id,
        header: "Graduation\nRate",
        accessor: (r) => r.inst.metrics[VARIABLES.graduationRate.id] as number | null,
        render: (r) => fmtPercent(r.inst.metrics[VARIABLES.graduationRate.id]),
        align: "right",
      },
      {
        id: VARIABLES.usNewsRank.id,
        header: "US News Rank\nwithin Category",
        accessor: (r) => r.inst.metrics[VARIABLES.usNewsRank.id] as number | null,
        align: "right",
      },
    ],
    [],
  );

  if (error) {
    return (
      <div className="rounded-lg border border-rule bg-panel p-4 text-sm text-oxblood">
        Failed to load institution data: {error}
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <FilterPanel
        defs={allFilters}
        state={filters}
        onChange={(next) => setFilters(pruneStatesToRegion(next, regionIdx))}
        onReset={() => setFilters(DEFAULT_FILTERS)}
      />
      <div className="rounded-lg border border-rule bg-panel p-5">
        {!institutions ? (
          <p className="p-3 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Loading institutions…
          </p>
        ) : (
          <DataTable
            rows={rows}
            columns={columns}
            rowKey={(r) => r.inst.unitid}
            pageSize={25}
            searchPlaceholder="Search universities…"
            initialSort={{ columnId: "rank", dir: "asc" }}
          />
        )}
      </div>
    </div>
  );
}
