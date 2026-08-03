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
 * Cost After Scholarship — net price by family-income band.
 *
 * Mirrors VaiTool: fetch the typed slice from /api, keep light local state, and
 * drive the shared DataTable. The five net-price-by-income-band currency vars
 * become columns, plus an "Average" column (mean of the available bands per
 * school). The legacy National / Other-4-Year toggle is a declarative `select`
 * FilterDef on the `nationalUniversity` flag — no magic ids.
 */

/** The five income bands, in order, with display headers. */
const BANDS: { id: string; header: string }[] = [
  { id: VARIABLES.net_price_0_30k.id, header: "$0–30k" },
  { id: VARIABLES.net_price_30_48k.id, header: "$30–48k" },
  { id: VARIABLES.net_price_48_75k.id, header: "$48–75k" },
  { id: VARIABLES.net_price_75_110k.id, header: "$75–110k" },
  { id: VARIABLES.net_price_110k_plus.id, header: "$110k+" },
];

function num(v: Institution["metrics"][string]): number | null {
  return typeof v === "number" ? v : null;
}

function fmtCurrency(v: number | string | boolean | null): string {
  return typeof v === "number" ? `$${Math.round(v).toLocaleString("en-US")}` : "—";
}

export default function CasTool() {
  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({});

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

  // Filters mirror the chart tools: classification, control, region, state, and
  // a US-News-rank range (bounds read from the data).
  const regionIdx = useMemo(() => buildRegionIndex(institutions), [institutions]);
  const defs = useMemo<FilterDef[]>(() => {
    let rankMin = Infinity;
    let rankMax = -Infinity;
    institutions?.forEach((i) => {
      const r = num(i.metrics[VARIABLES.usNewsRank.id]);
      if (r !== null) {
        rankMin = Math.min(rankMin, r);
        rankMax = Math.max(rankMax, r);
      }
    });
    return [
      {
        kind: "select",
        id: "national",
        label: "Classification",
        field: VARIABLES.nationalUniversity.id,
        options: [
          { label: "National", value: true },
          { label: "Regional & Liberal Arts", value: false },
        ],
      },
      {
        kind: "select",
        id: "control",
        label: "Public / Private",
        field: VARIABLES.publicPrivate.id,
        options: [
          { label: "Public", value: "Public" },
          { label: "Private", value: "Private" },
        ],
      },
      regionDef(regionIdx),
      stateDef(regionIdx, typeof filters.region === "string" ? filters.region : null),
      {
        kind: "range",
        id: "usn",
        label: "US News Rank within Category",
        field: VARIABLES.usNewsRank.id,
        min: Number.isFinite(rankMin) ? rankMin : 1,
        max: Number.isFinite(rankMax) ? rankMax : 1,
        step: 1,
      },
    ];
  }, [institutions, regionIdx, filters.region]);

  const rows = useMemo<Institution[]>(() => {
    if (!institutions) return [];
    return applyFilters(institutions, defs, filters);
  }, [institutions, defs, filters]);

  const columns = useMemo<Column<Institution>[]>(
    () => [
      {
        id: "name",
        header: "University",
        accessor: (r) => r.name,
        render: (r) => <CollegeNavLink unitid={r.unitid} name={r.name} />,
        searchable: true,
      },
      ...BANDS.map(
        (b): Column<Institution> => ({
          id: b.id,
          header: b.header,
          accessor: (r) => num(r.metrics[b.id]),
          render: (r) => fmtCurrency(r.metrics[b.id]),
          align: "right",
        }),
      ),
      {
        // The IPEDS-reported, enrollment-weighted average net price (from
        // Navigator via data.ts's `avg_net_price`) — NOT the mean of the 5
        // bands, which understates it. Keeps CAS == VAC == College Navigator.
        id: "average",
        header: "Average",
        accessor: (r) => num(r.metrics[VARIABLES.avg_net_price.id]),
        render: (r) => fmtCurrency(r.metrics[VARIABLES.avg_net_price.id]),
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
        defs={defs}
        state={filters}
        onChange={(next) => setFilters(pruneStatesToRegion(next, regionIdx))}
        onReset={() => setFilters({})}
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
            rowKey={(r) => r.unitid}
            pageSize={25}
            searchPlaceholder="Search universities…"
            initialSort={{ columnId: "name", dir: "asc" }}
          />
        )}
      </div>
    </div>
  );
}
