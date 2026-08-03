"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import {
  CartesianGrid,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import ChartCard from "@/components/Chart";
import CollegeNavLink from "@/components/CollegeNavLink";
import FilterPanel from "@/components/FilterPanel";
import InstitutionPicker, { type PickerItem } from "@/components/InstitutionPicker";
import { stableColor } from "@/lib/colors";
import { applyFilters, type FilterDef, type FilterState } from "@/lib/filters";
import { VARIABLES } from "@/lib/variables";
import { buildRegionIndex, regionDef, stateDef, pruneStatesToRegion } from "@/lib/regions";
import type { ApiResponse, Institution } from "@/lib/types";

/**
 * Value-Added & Cost — Value-Added score (x) vs net price (y), split into four
 * series by National × Control. Mirrors VamTool exactly (declarative FilterDefs,
 * the shared InstitutionPicker, the highlight star + hover ring, and the same
 * wheel-zoom / drag-pan). The Y metric is the net price for a SELECTED family-
 * income band; an income-band selector switches it. Schools missing the selected
 * band's net price are simply not plotted.
 */

interface Point {
  x: number;
  y: number;
  unitid: number;
  name: string;
  state: string | null;
}

interface Group {
  key: string;
  label: string;
  color: string;
  national: boolean;
  control: string;
}

const GROUPS: Group[] = [
  { key: "np", label: "National Public", color: "#0c6b61", national: true, control: "Public" },
  { key: "npr", label: "National Private", color: "#9b3a2e", national: true, control: "Private" },
  { key: "op", label: "Regional & Liberal Arts Public", color: "#3b5b78", national: false, control: "Public" },
  { key: "opr", label: "Regional & Liberal Arts Private", color: "#d99016", national: false, control: "Private" },
];

/**
 * Income bands; `id` selects the Y metric (a net-price var). "Average" — the
 * mean net price across all bands — leads and is the default view.
 */
const BANDS: { id: string; label: string }[] = [
  { id: VARIABLES.avg_net_price.id, label: "Average" },
  { id: VARIABLES.net_price_0_30k.id, label: "$0–30k" },
  { id: VARIABLES.net_price_30_48k.id, label: "$30–48k" },
  { id: VARIABLES.net_price_48_75k.id, label: "$48–75k" },
  { id: VARIABLES.net_price_75_110k.id, label: "$75–110k" },
  { id: VARIABLES.net_price_110k_plus.id, label: "$110k+" },
];

const C_RULE = "#d8cbb1";
const C_INK_SOFT = "#5a6472";
const MONO = "var(--font-mono)";
const AXIS_TICK = { fontSize: 11, fill: C_INK_SOFT, fontFamily: MONO } as const;

const VAD = VARIABLES.vaDistance.id;
const NAT = VARIABLES.nationalUniversity.id;
const CTRL = VARIABLES.publicPrivate.id;
const USN = VARIABLES.usNewsRank.id;

function n(v: Institution["metrics"][string]): number | null {
  return typeof v === "number" ? v : null;
}

function fmtCurrency(v: number): string {
  return `$${Math.round(v).toLocaleString("en-US")}`;
}

/**
 * Marker for a selected/highlighted school — a colored ring (the same outline
 * used for hover/pin), which reads better than the old star. Recharts calls it
 * per point with computed `cx`/`cy` and the Scatter's `fill` (stable color).
 */
function SelectedRing(props: { cx?: number; cy?: number; fill?: string }) {
  const { cx, cy, fill } = props;
  if (cx == null || cy == null) return <g />;
  return (
    <g>
      <circle cx={cx} cy={cy} r={8} fill="none" stroke={fill} strokeWidth={2.5} />
      <circle cx={cx} cy={cy} r={3} fill={fill} />
    </g>
  );
}

export default function VacTool() {
  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({});
  // Multi-select: several schools stay highlighted until cleared.
  const [selected, setSelected] = useState<number[]>([]);
  const [hovered, setHovered] = useState<number | null>(null);
  // Click a dot to pin a sticky popover; hovering another then shows a second
  // (transient) tooltip, so two schools' numbers read at once.
  const [pinned, setPinned] = useState<number | null>(null);

  // Coalesce picker cross-highlight hovers to one update per frame (see VamTool).
  const rafHover = useRef<number | null>(null);
  const pendingHover = useRef<number | null>(null);
  const setHoveredThrottled = (id: number | null) => {
    pendingHover.current = id;
    if (rafHover.current != null) return;
    rafHover.current = requestAnimationFrame(() => {
      rafHover.current = null;
      setHovered(pendingHover.current);
    });
  };
  const [bandId, setBandId] = useState<string>(BANDS[0].id);

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

  const bandLabel = BANDS.find((b) => b.id === bandId)?.label ?? "";

  const regionIdx = useMemo(() => buildRegionIndex(institutions), [institutions]);
  const defs = useMemo<FilterDef[]>(() => {
    let rankMin = Infinity;
    let rankMax = -Infinity;
    institutions?.forEach((i) => {
      const r = n(i.metrics[USN]);
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
        field: NAT,
        options: [
          { label: "National", value: true },
          { label: "Regional & Liberal Arts", value: false },
        ],
      },
      {
        kind: "select",
        id: "control",
        label: "Public / Private",
        field: CTRL,
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
        field: USN,
        min: Number.isFinite(rankMin) ? rankMin : 1,
        max: Number.isFinite(rankMax) ? rankMax : 1,
        step: 1,
      },
    ];
  }, [institutions, regionIdx, filters.region]);

  const filtered = useMemo(() => {
    if (!institutions) return [];
    return applyFilters(institutions, defs, filters).filter(
      (i) => n(i.metrics[VAD]) !== null && n(i.metrics[bandId]) !== null,
    );
  }, [institutions, defs, filters, bandId]);

  const seriesData = useMemo(() => {
    const map = new Map<string, Point[]>(GROUPS.map((g) => [g.key, []]));
    for (const i of filtered) {
      const isNat = i.metrics[NAT] === true;
      const ctrl = i.metrics[CTRL];
      const g = GROUPS.find((g) => g.national === isNat && g.control === ctrl);
      if (!g) continue;
      map.get(g.key)!.push({
        // x = Net Price (cost), y = Value-Added score.
        x: n(i.metrics[bandId])!,
        y: n(i.metrics[VAD])!,
        unitid: i.unitid,
        name: i.name,
        state: i.state,
      });
    }
    return map;
  }, [filtered, bandId]);

  const pointFor = (unitid: number | null): Point[] => {
    if (unitid == null) return [];
    const inst = filtered.find((i) => i.unitid === unitid);
    if (!inst) return [];
    return [
      {
        x: n(inst.metrics[bandId])!,
        y: n(inst.metrics[VAD])!,
        unitid: inst.unitid,
        name: inst.name,
        state: inst.state,
      },
    ];
  };

  const selectedPoints = useMemo(
    () => selected.flatMap((id) => pointFor(id)),
    [selected, filtered, bandId], // eslint-disable-line react-hooks/exhaustive-deps
  );
  // Starred (selected) schools skip the hover ring (they carry a star); a
  // pinned school still responds to hover (its transient card rides on top).
  const hoveredPoint = useMemo(
    () => (hovered != null && selected.includes(hovered) ? [] : pointFor(hovered)),
    [hovered, selected, filtered, bandId], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const pinnedPoint = useMemo(
    () => pointFor(pinned),
    [pinned, filtered, bandId], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // Picker items: schools with a VA score (band-independent), enriched for filters.
  const items = useMemo<PickerItem[]>(() => {
    if (!institutions) return [];
    return institutions
      .filter((i) => n(i.metrics[VAD]) !== null)
      .map((i) => ({
        unitid: i.unitid,
        name: i.name,
        region: i.region,
        state: i.state,
        national: i.metrics[NAT] === true ? true : i.metrics[NAT] === false ? false : null,
        usNewsRank: n(i.metrics[USN]),
      }));
  }, [institutions]);

  // ── Zoom / pan ──────────────────────────────────────────────
  const extent = useMemo(() => {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const arr of seriesData.values())
      for (const p of arr) {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
    if (!Number.isFinite(minX))
      return { x: [0, 50000] as [number, number], y: [-30, 30] as [number, number] };
    const padX = (maxX - minX) * 0.06 || 1;
    const padY = (maxY - minY) * 0.06 || 1;
    return {
      x: [minX - padX, maxX + padX] as [number, number],
      y: [minY - padY, maxY + padY] as [number, number],
    };
  }, [seriesData]);

  const [view, setView] = useState<{ x: [number, number]; y: [number, number] } | null>(null);
  const xDom = view?.x ?? extent.x;
  const yDom = view?.y ?? extent.y;

  /** Button zoom centred on the current view (trackpads can't scroll-zoom). */
  const zoomBy = (scale: number) =>
    setView((v) => {
      const cx = v?.x ?? extentRef.current.x;
      const cy = v?.y ?? extentRef.current.y;
      const midX = (cx[0] + cx[1]) / 2;
      const midY = (cy[0] + cy[1]) / 2;
      const nSpanX = Math.max((cx[1] - cx[0]) * scale, 1);
      const nSpanY = Math.max((cy[1] - cy[0]) * scale, 1);
      return {
        x: [midX - nSpanX / 2, midX + nSpanX / 2],
        y: [midY - nSpanY / 2, midY + nSpanY / 2],
      };
    });

  const plotRef = useRef<HTMLDivElement>(null);
  const extentRef = useRef(extent);
  useEffect(() => {
    extentRef.current = extent;
  }, [extent]);
  // plot-area insets inside ChartCard's plot div (px-3/py-5 padding + chart margins + axes)
  // y-axis now shows Value-Added integers (narrow), like VAM — match its L inset.
  const INSET = { L: 68, R: 36, T: 28, B: 64 };

  // Plot pixel size for the hover-highlight overlay projection (see VamTool).
  const [plotSize, setPlotSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setPlotSize({ w: r.width, h: r.height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const pw = rect.width - INSET.L - INSET.R;
      const ph = rect.height - INSET.T - INSET.B;
      if (pw <= 0 || ph <= 0) return;
      const fx = Math.min(1, Math.max(0, (e.clientX - rect.left - INSET.L) / pw));
      const fyTop = Math.min(1, Math.max(0, (e.clientY - rect.top - INSET.T) / ph));
      setView((v) => {
        const cx = v?.x ?? extentRef.current.x;
        const cy = v?.y ?? extentRef.current.y;
        const spanX = cx[1] - cx[0];
        const spanY = cy[1] - cy[0];
        const dataX = cx[0] + fx * spanX;
        const dataY = cy[0] + (1 - fyTop) * spanY;
        const scale = e.deltaY > 0 ? 1.12 : 0.89;
        const nSpanX = Math.max(spanX * scale, 1);
        const nSpanY = Math.max(spanY * scale, 1);
        return {
          x: [dataX - fx * nSpanX, dataX + (1 - fx) * nSpanX],
          y: [dataY - (1 - fyTop) * nSpanY, dataY + fyTop * nSpanY],
        };
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const drag = useRef<{ x: number; y: number; dom: { x: [number, number]; y: [number, number] } } | null>(null);
  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    drag.current = { x: e.clientX, y: e.clientY, dom: { x: [xDom[0], xDom[1]], y: [yDom[0], yDom[1]] } };
  }
  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    const d = drag.current;
    if (!d || !plotRef.current) return;
    const rect = plotRef.current.getBoundingClientRect();
    const pw = rect.width - INSET.L - INSET.R;
    const ph = rect.height - INSET.T - INSET.B;
    if (pw <= 0 || ph <= 0) return;
    const spanX = d.dom.x[1] - d.dom.x[0];
    const spanY = d.dom.y[1] - d.dom.y[0];
    const ddx = -((e.clientX - d.x) / pw) * spanX;
    const ddy = ((e.clientY - d.y) / ph) * spanY;
    setView({
      x: [d.dom.x[0] + ddx, d.dom.x[1] + ddx],
      y: [d.dom.y[0] + ddy, d.dom.y[1] + ddy],
    });
  }
  function endPan() {
    drag.current = null;
  }
  // A pointer-up that didn't travel is a click, not a pan: pin the nearest dot
  // (or dismiss on empty space). Nearest-point search runs only on click.
  function onPointerUp(e: ReactPointerEvent<HTMLDivElement>) {
    const d = drag.current;
    drag.current = null;
    if (!d || !plotRef.current) return;
    if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 5) return; // was a pan
    const rect = plotRef.current.getBoundingClientRect();
    const innerW = rect.width - INSET.L - INSET.R;
    const innerH = rect.height - INSET.T - INSET.B;
    if (innerW <= 0 || innerH <= 0) return;
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    let best: number | null = null;
    let bestD = 14; // px hit radius
    for (const arr of seriesData.values())
      for (const p of arr) {
        const px = INSET.L + ((p.x - xDom[0]) / (xDom[1] - xDom[0])) * innerW;
        const py = INSET.T + (1 - (p.y - yDom[0]) / (yDom[1] - yDom[0])) * innerH;
        const dd = Math.hypot(px - sx, py - sy);
        if (dd < bestD) {
          bestD = dd;
          best = p.unitid;
        }
      }
    setPinned((prev) => (best != null && prev === best ? null : best));
  }

  if (error) {
    return (
      <div className="rounded-lg border border-rule bg-panel p-4 text-sm text-oxblood">
        Failed to load institution data: {error}
      </div>
    );
  }

  const totalPlotted = [...seriesData.values()].reduce((a, v) => a + v.length, 0);

  // Project a data point to plot-pixel coords (same math as pan/zoom), or null
  // if out of view. Drives the hover ring + the pinned card.
  const projectPoint = (p: Point) => {
    if (plotSize.w === 0) return null;
    const innerW = plotSize.w - INSET.L - INSET.R;
    const innerH = plotSize.h - INSET.T - INSET.B;
    const sx = INSET.L + ((p.x - xDom[0]) / (xDom[1] - xDom[0])) * innerW;
    const sy = INSET.T + (1 - (p.y - yDom[0]) / (yDom[1] - yDom[0])) * innerH;
    if (sx < INSET.L - 2 || sx > plotSize.w - INSET.R + 2 || sy < INSET.T - 2 || sy > plotSize.h - INSET.B + 2)
      return null;
    return { x: sx, y: sy };
  };
  const hoverPos = hoveredPoint[0] ? projectPoint(hoveredPoint[0]) : null;
  const pinPos = pinnedPoint[0] ? projectPoint(pinnedPoint[0]) : null;

  // Memoized on real inputs (NOT `hovered`) so cross-highlighting never
  // re-renders the 1,004 points. See VamTool for the rationale.
  const chart = useMemo(
    () => (
      <ScatterChart margin={{ top: 8, right: 24, bottom: 24, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={C_RULE} />
        <XAxis
          type="number"
          dataKey="x"
          name="Net Price"
          domain={xDom}
          allowDataOverflow
          tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
          tick={AXIS_TICK}
          stroke={C_RULE}
          tickLine={{ stroke: C_RULE }}
          label={{ value: bandId === VARIABLES.avg_net_price.id ? "Average Net Price" : `Net Price · ${bandLabel}`, position: "insideBottom", offset: -12, fontSize: 11, fill: C_INK_SOFT, fontFamily: MONO }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Value-Added score"
          domain={yDom}
          allowDataOverflow
          tickFormatter={(v: number) => `${Math.round(v)}`}
          tick={AXIS_TICK}
          stroke={C_RULE}
          tickLine={{ stroke: C_RULE }}
          width={48}
          label={{ value: "Value-Added score", angle: -90, position: "insideLeft", fontSize: 11, fill: C_INK_SOFT, fontFamily: MONO }}
        />
        <ZAxis range={[36, 36]} />
        <Tooltip cursor={false} isAnimationActive={false} wrapperStyle={{ transition: "none" }} content={<PointTooltip bandLabel={bandLabel} pinnedId={pinned} />} />
        {GROUPS.map((g) => (
          <Scatter
            key={g.key}
            name={g.label}
            data={seriesData.get(g.key)}
            fill={g.color}
            fillOpacity={selected.length > 0 ? 0.5 : 0.72}
            isAnimationActive={false}
          />
        ))}
        {selectedPoints.map((p) => (
          <Scatter
            key={p.unitid}
            name="Selected"
            data={[p]}
            legendType="none"
            fill={stableColor(p.unitid)}
            shape={<SelectedRing />}
            isAnimationActive={false}
          />
        ))}
      </ScatterChart>
    ),
    // hovered intentionally excluded; pinned included so the baked <Tooltip>
    // element knows which dot to stay silent for.
    [xDom, yDom, seriesData, selectedPoints, selected.length, bandId, bandLabel, pinned],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)_240px]">
      <FilterPanel
        defs={defs}
        state={filters}
        onChange={(next) => setFilters(pruneStatesToRegion(next, regionIdx))}
        onReset={() => setFilters({})}
      />

      <ChartCard
        title="Value-Added vs. Cost"
        subtitle={`${totalPlotted} plotted · ${bandId === VARIABLES.avg_net_price.id ? "average net price across all income bands" : `net price for ${bandLabel} income`} · click a dot to pin · scroll or +/− to zoom, drag to pan${selected.length > 0 && selectedPoints.length === 0 ? " · selection filtered out" : ""}`}
        height={640}
        plotRef={plotRef}
        plotProps={{
          onPointerDown,
          onPointerMove,
          onPointerUp,
          onPointerLeave: endPan,
          className: "cursor-grab touch-none select-none active:cursor-grabbing",
        }}
        overlay={
          (hoverPos || pinPos) && (
            <>
              <svg className="absolute inset-0 h-full w-full">
                {pinPos && (
                  <>
                    <circle cx={pinPos.x} cy={pinPos.y} r={10} fill="none" stroke="#1b2430" strokeWidth={2} />
                    <circle cx={pinPos.x} cy={pinPos.y} r={3.5} fill="#1b2430" />
                  </>
                )}
                {hoverPos && (
                  <>
                    <circle cx={hoverPos.x} cy={hoverPos.y} r={9} fill="none" stroke="#0c6b61" strokeWidth={1.5} />
                    <circle cx={hoverPos.x} cy={hoverPos.y} r={3} fill="#0c6b61" />
                  </>
                )}
              </svg>
              {hoverPos && hoveredPoint[0] && (
                <VacCard point={hoveredPoint[0]} x={hoverPos.x} y={hoverPos.y} bandLabel={bandLabel} />
              )}
              {pinPos && pinnedPoint[0] && (
                <VacCard point={pinnedPoint[0]} x={pinPos.x} y={pinPos.y} bandLabel={bandLabel} pinned onClose={() => setPinned(null)} />
              )}
            </>
          )
        }
        legend={
          <div className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {GROUPS.map((g) => (
              <span
                key={g.key}
                className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.1em] text-ink-soft"
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: g.color }} />
                {g.label}
              </span>
            ))}
          </div>
        }
        actions={
          <>
            <div className="flex h-8 items-center rounded-md border border-rule bg-paper p-0.5">
              {BANDS.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setBandId(b.id)}
                  className={[
                    "flex h-full cursor-pointer items-center rounded px-2 font-mono text-[10px] uppercase tracking-[0.08em] tabular-nums transition-colors",
                    bandId === b.id ? "bg-ink text-paper" : "text-ink-soft hover:bg-panel hover:text-ink",
                  ].join(" ")}
                >
                  {b.label}
                </button>
              ))}
            </div>
            <div className="flex h-8 overflow-hidden rounded-md border border-rule">
              <button onClick={() => zoomBy(0.8)} aria-label="Zoom in" title="Zoom in"
                className="flex h-full w-8 cursor-pointer items-center justify-center bg-paper font-mono text-[15px] leading-none text-ink-soft transition-colors hover:bg-panel hover:text-ink">+</button>
              <button onClick={() => zoomBy(1.25)} aria-label="Zoom out" title="Zoom out"
                className="flex h-full w-8 cursor-pointer items-center justify-center border-l border-rule bg-paper font-mono text-[15px] leading-none text-ink-soft transition-colors hover:bg-panel hover:text-ink">−</button>
            </div>
            {view && (
              <button
                onClick={() => setView(null)}
                className="flex h-8 cursor-pointer items-center rounded-md border border-rule bg-paper px-3 font-mono text-[11px] uppercase tracking-[0.12em] text-teal transition-colors hover:border-teal hover:text-teal-bright"
              >
                Reset zoom
              </button>
            )}
          </>
        }
      >
        {chart}
      </ChartCard>

      <InstitutionPicker
        items={items}
        selected={selected}
        onToggle={(id) =>
          setSelected((prev) =>
            prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
          )
        }
        onClear={() => setSelected([])}
        colorFor={stableColor}
        hovered={hovered}
        onHover={setHoveredThrottled}
        loading={!institutions}
        verb="highlighted"
      />
    </div>
  );
}

/**
 * Overlay info card for both the transient hover preview and the sticky pinned
 * popover. When `pinned` it's interactive (name links to College Navigator, ×
 * dismisses); otherwise a pass-through preview. Flips below the dot near the top.
 */
function VacCard({
  point,
  x,
  y,
  bandLabel,
  pinned,
  onClose,
}: {
  point: Point;
  x: number;
  y: number;
  bandLabel: string;
  pinned?: boolean;
  onClose?: () => void;
}) {
  return (
    <div
      className={`absolute -translate-x-1/2 rounded-md border bg-panel px-3 py-2 text-xs ${
        y < 96 ? "translate-y-3" : "-translate-y-[calc(100%+14px)]"
      } ${pinned ? "pointer-events-auto border-ink/40 pr-6 shadow-md" : "pointer-events-none border-rule shadow-sm"}`}
      style={{ left: x, top: y }}
      onPointerDown={pinned ? (e) => e.stopPropagation() : undefined}
    >
      {pinned && onClose && (
        <button
          onClick={onClose}
          aria-label="Unpin"
          title="Unpin"
          className="absolute right-1 top-1 rounded px-1 font-mono text-[11px] leading-none text-ink-soft transition-colors hover:text-oxblood"
        >
          &times;
        </button>
      )}
      <p className="whitespace-nowrap font-display text-sm font-semibold text-ink">
        {pinned ? <CollegeNavLink unitid={point.unitid} name={point.name} /> : point.name}
      </p>
      {point.state && (
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft">{point.state}</p>
      )}
      <p className="mt-1 whitespace-nowrap font-mono tabular-nums text-ink-soft">
        Value-Added: <span className="text-ink">{point.y.toFixed(1)}</span>
      </p>
      <p className="whitespace-nowrap font-mono tabular-nums text-ink-soft">
        Net Price ({bandLabel}): <span className="text-ink">{fmtCurrency(point.x)}</span>
      </p>
    </div>
  );
}

interface TooltipPayload {
  payload: Point;
}

function PointTooltip({
  active,
  payload,
  bandLabel,
  pinnedId,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  bandLabel: string;
  pinnedId?: number | null;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  // The pinned dot already shows its sticky card — no hover tooltip on top.
  if (p.unitid === pinnedId) return null;
  return (
    <div className="rounded-md border border-rule bg-panel px-3 py-2 text-xs">
      <p className="font-display text-sm font-semibold text-ink">{p.name}</p>
      {p.state && (
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft">
          {p.state}
        </p>
      )}
      <p className="mt-1 font-mono tabular-nums text-ink-soft">
        Value-Added: <span className="text-ink">{p.y.toFixed(1)}</span>
      </p>
      <p className="font-mono tabular-nums text-ink-soft">
        Net Price ({bandLabel}): <span className="text-ink">{fmtCurrency(p.x)}</span>
      </p>
    </div>
  );
}
