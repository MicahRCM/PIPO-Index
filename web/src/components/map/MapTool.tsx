"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import usAtlas from "us-atlas/states-10m.json";
import Select from "@/components/Select";
import CollegeNavLink from "@/components/CollegeNavLink";
import FilterPanel from "@/components/FilterPanel";
import { applyFilters, type FilterDef, type FilterState } from "@/lib/filters";
import { VARIABLES, type VariableId } from "@/lib/variables";
import { buildRegionIndex, regionDef, stateDef, pruneStatesToRegion } from "@/lib/regions";
import type { ApiResponse, Institution } from "@/lib/types";
import { buildColorScale, formatMetric } from "./mapColor";
import { DEFAULT_METRIC, MAP_METRICS, MAP_METRIC_GROUPS } from "./metrics";

/**
 * The Atlas Map — every institution plotted on a geoAlbersUsa projection of the
 * US, each dot colored by a chosen indicator. States are hairline paper shapes
 * from the us-atlas TopoJSON; institutions are projected from their directory
 * lng/lat (points outside the US, and the ~21 schools with no coordinates, are
 * skipped). The shared FilterPanel governs which dots show; the variable
 * selector + duotone legend govern how they read.
 */

const WIDTH = 975;
const HEIGHT = 610;
const NAT = VARIABLES.nationalUniversity.id;
const CTRL = VARIABLES.publicPrivate.id;
const USN = VARIABLES.usNewsRank.id;

const C_RULE = "#d8cbb1";
const C_PAPER = "#f4eee1";
const C_INK = "#1b2430";

function num(v: Institution["metrics"][string]): number | null {
  return typeof v === "number" ? v : null;
}

/** A school that successfully projected onto the map. */
interface PlottedPoint {
  unitid: number;
  name: string;
  state: string | null;
  city: string | null;
  x: number;
  y: number;
  value: number;
}

// us-atlas ships geographic (lng/lat) TopoJSON; project states + points alike.
const TOPO = usAtlas as unknown as Topology;
const STATES_OBJ = TOPO.objects.states as GeometryCollection;

export default function MapTool() {
  const [institutions, setInstitutions] = useState<Institution[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({});
  const [metricId, setMetricId] = useState<VariableId>(DEFAULT_METRIC);
  const [hovered, setHovered] = useState<number | null>(null);
  const [pinned, setPinned] = useState<number | null>(null);

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

  // Projection + state geometry — built once. geoAlbersUsa insets AK/HI.
  const geo = useMemo(() => {
    const states = feature(TOPO, STATES_OBJ) as GeoJSON.FeatureCollection;
    const projection = geoAlbersUsa().fitSize([WIDTH, HEIGHT], states);
    const path = geoPath(projection);
    const statesPath = states.features
      .map((f) => path(f))
      .filter((d): d is string => d !== null);
    const borders = mesh(TOPO, STATES_OBJ, (a, b) => a !== b);
    const bordersPath = path(borders) ?? "";
    const project = (lng: number, lat: number) => projection([lng, lat]);
    return { statesPath, bordersPath, project };
  }, []);

  const metric = MAP_METRICS[metricId];
  const variable = VARIABLES[metricId];

  const regionIdx = useMemo(() => buildRegionIndex(institutions), [institutions]);
  const defs = useMemo<FilterDef[]>(() => {
    let rankMin = Infinity;
    let rankMax = -Infinity;
    institutions?.forEach((i) => {
      const r = num(i.metrics[USN]);
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

  // Filter, then project. Only schools with coords + a non-null metric value plot.
  const plotted = useMemo<PlottedPoint[]>(() => {
    if (!institutions) return [];
    const out: PlottedPoint[] = [];
    for (const i of applyFilters(institutions, defs, filters)) {
      const value = num(i.metrics[metricId]);
      if (value === null) continue;
      if (i.latitude == null || i.longitude == null) continue;
      const xy = geo.project(i.longitude, i.latitude);
      if (!xy) continue; // outside geoAlbersUsa (e.g. territories)
      out.push({
        unitid: i.unitid,
        name: i.name,
        state: i.state,
        city: i.city ?? null,
        x: xy[0],
        y: xy[1],
        value,
      });
    }
    return out;
  }, [institutions, defs, filters, metricId, geo]);

  const scale = useMemo(() => {
    if (plotted.length === 0) return null;
    return buildColorScale(
      plotted.map((p) => p.value),
      metric?.diverging ?? false,
      metric?.reverse ?? false,
    );
  }, [plotted, metric]);

  // Pinned persists (concentric ink ring + interactive tooltip); hovering
  // another dot shows a transient teal ring/tooltip on top — same model as
  // VAM/VAC. A hovered dot that IS the pinned one doesn't double-draw.
  const pinnedPoint = useMemo(
    () => (pinned != null ? plotted.find((p) => p.unitid === pinned) ?? null : null),
    [plotted, pinned],
  );
  const hoveredPoint = useMemo(
    () => (hovered != null && hovered !== pinned ? plotted.find((p) => p.unitid === hovered) ?? null : null),
    [plotted, hovered, pinned],
  );

  // Coalesce nearest-dot hover to one update per frame (see VAM/VAC).
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

  // ── Zoom / pan ──────────────────────────────────────────────
  // A single {k, tx, ty} transform on the map group. Dots keep constant screen
  // size (radius / k). Wheel zooms toward the cursor; drag pans; +/− buttons
  // and reset give trackpad users a mouse-free path.
  const [t, setT] = useState({ k: 1, tx: 0, ty: 0 });
  const svgRef = useRef<SVGSVGElement | null>(null);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);

  const clampT = (k: number, tx: number, ty: number) => {
    const kk = Math.max(1, Math.min(12, k));
    // keep the map from being dragged completely out of view
    const maxX = 0, minX = WIDTH * (1 - kk);
    const maxY = 0, minY = HEIGHT * (1 - kk);
    return { k: kk, tx: Math.max(minX, Math.min(maxX, tx)), ty: Math.max(minY, Math.min(maxY, ty)) };
  };

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const px = ((e.clientX - rect.left) / rect.width) * WIDTH;
      const py = ((e.clientY - rect.top) / rect.height) * HEIGHT;
      setT((v) => {
        const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        const k = Math.max(1, Math.min(12, v.k * factor));
        // zoom about the cursor: data point under the cursor stays fixed
        const tx = px - ((px - v.tx) * k) / v.k;
        const ty = py - ((py - v.ty) * k) / v.k;
        return clampT(k, tx, ty);
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const zoomBy = (factor: number) =>
    setT((v) => {
      const k = Math.max(1, Math.min(12, v.k * factor));
      // zoom about the center of the viewport
      const cx = WIDTH / 2, cy = HEIGHT / 2;
      const tx = cx - ((cx - v.tx) * k) / v.k;
      const ty = cy - ((cy - v.ty) * k) / v.k;
      return clampT(k, tx, ty);
    });

  // Nearest plotted dot to a screen point (forgiving hit radius), accounting for
  // the current pan/zoom transform. Lets hover + click land without pixel-perfect
  // aim on the 3px dots — the map's version of Recharts' proximity detection.
  const nearestDot = (clientX: number, clientY: number, maxPx = 12): number | null => {
    const el = svgRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    let best: number | null = null;
    let bestD = maxPx;
    for (const p of plotted) {
      const sx = rect.left + ((p.x * t.k + t.tx) / WIDTH) * rect.width;
      const sy = rect.top + ((p.y * t.k + t.ty) / HEIGHT) * rect.height;
      const d = Math.hypot(sx - clientX, sy - clientY);
      if (d < bestD) {
        bestD = d;
        best = p.unitid;
      }
    }
    return best;
  };

  const onPointerDown = (e: ReactPointerEvent<SVGSVGElement>) => {
    drag.current = { x: e.clientX, y: e.clientY, tx: t.tx, ty: t.ty, moved: false };
    (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: ReactPointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (d) {
      // A pointer held down = panning.
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 4) d.moved = true;
      const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
      const dx = ((e.clientX - d.x) / rect.width) * WIDTH;
      const dy = ((e.clientY - d.y) / rect.height) * HEIGHT;
      setT(() => clampT(t.k, d.tx + dx, d.ty + dy));
    } else {
      // No button = hovering; highlight the nearest dot.
      setHoveredThrottled(nearestDot(e.clientX, e.clientY));
    }
  };
  const onPointerUp = (e: ReactPointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    drag.current = null;
    if (!d || d.moved) return; // a pan, not a click
    // Click: pin the nearest dot (toggle), or dismiss when clicking empty space.
    const id = nearestDot(e.clientX, e.clientY);
    setPinned((prev) => (id != null && prev === id ? null : id));
  };
  const endDrag = () => {
    drag.current = null;
    setHoveredThrottled(null);
  };
  const zoomed = t.k > 1.001;

  // The 1,004 base dots are memoized on the data/scale/zoom — NOT on hover/pin —
  // so hovering repaints only the single highlight overlay, not every dot.
  const baseDots = useMemo(
    () => (
      // pointer-events:none — hover/click are handled at the svg level via
      // nearest-dot detection, so moves always reach the pan/hover handlers.
      <g pointerEvents="none">
        {plotted.map((p) => (
          <circle
            key={p.unitid}
            cx={p.x}
            cy={p.y}
            r={3 / t.k}
            fill={scale ? scale.color(p.value) : C_INK}
            stroke="rgba(27,36,48,0.35)"
            strokeWidth={0.5 / t.k}
          />
        ))}
      </g>
    ),
    [plotted, scale, t.k],
  );

  if (error) {
    return (
      <div className="rounded-lg border border-rule bg-panel p-4 text-sm text-oxblood">
        Failed to load institution data: {error}
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[200px_minmax(0,1fr)]">
      <FilterPanel defs={defs} state={filters} onChange={(next) => setFilters(pruneStatesToRegion(next, regionIdx))} onReset={() => setFilters({})} />

      <section className="flex h-full flex-col rounded-lg border border-rule bg-panel">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-rule px-6 py-4">
          <div>
            <h2 className="font-display text-lg font-semibold tracking-tight text-ink">
              {variable.label} across the United States
            </h2>
            <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
              {plotted.length.toLocaleString()} institutions plotted
              {institutions ? ` of ${institutions.length.toLocaleString()}` : ""}
            </p>
          </div>
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-soft">
              Color by
            </span>
            <Select
              ariaLabel="Color by"
              className="min-w-[220px]"
              value={metricId}
              onChange={(v) => setMetricId(v as VariableId)}
              groups={MAP_METRIC_GROUPS.map((group) => ({
                label: group.label,
                options: group.metrics.map((m) => ({
                  label: VARIABLES[m.id].label,
                  value: m.id,
                })),
              }))}
            />
          </label>
        </div>

        {scale && (
          <div className="border-b border-rule px-6 py-3">
            <Legend scale={scale} kind={variable.kind} diverging={metric?.diverging ?? false} reverse={metric?.reverse ?? false} />
          </div>
        )}

        <div className="relative min-h-0 flex-1 px-3 py-4">
          {/* Zoom controls */}
          <div className="absolute right-5 top-6 z-10 flex flex-col overflow-hidden rounded-md border border-rule bg-paper/90 shadow-sm backdrop-blur">
            <button
              onClick={() => zoomBy(1.5)}
              aria-label="Zoom in"
              title="Zoom in"
              className="px-2.5 py-1.5 font-mono text-[14px] leading-none text-ink-soft transition-colors hover:bg-panel hover:text-ink"
            >
              +
            </button>
            <button
              onClick={() => zoomBy(1 / 1.5)}
              aria-label="Zoom out"
              title="Zoom out"
              className="border-t border-rule px-2.5 py-1.5 font-mono text-[14px] leading-none text-ink-soft transition-colors hover:bg-panel hover:text-ink"
            >
              −
            </button>
            {zoomed && (
              <button
                onClick={() => setT({ k: 1, tx: 0, ty: 0 })}
                aria-label="Reset zoom"
                title="Reset zoom"
                className="border-t border-rule px-2.5 py-1.5 font-mono text-[10px] leading-none text-teal transition-colors hover:bg-panel"
              >
                ⟳
              </button>
            )}
          </div>

          <svg
            ref={svgRef}
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            // `select-none` + suppressing `dragstart` stop Windows Chrome from
            // starting a native HTML5 element/image drag on the second drag
            // (the "⊘ cancel-cursor, 1px-only pan" bug); Mac Chrome never
            // initiated that native drag, which is why it only showed on Windows.
            // No grab-hand cursor (per request) — the pan hand made it hard to
            // aim at dots; instead show a pointer only when a dot is under the
            // cursor, matching how VAM/VAC read.
            className="h-auto w-full touch-none select-none"
            style={{ cursor: hoveredPoint ? "pointer" : "default" }}
            role="img"
            aria-label={`US map of institutions colored by ${variable.label}`}
            onDragStart={(e) => e.preventDefault()}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={endDrag}
            onPointerLeave={endDrag}
          >
            <g transform={`translate(${t.tx},${t.ty}) scale(${t.k})`}>
              <g>
                {geo.statesPath.map((d, i) => (
                  <path key={i} d={d} fill={C_PAPER} stroke="none" />
                ))}
                <path
                  d={geo.bordersPath}
                  fill="none"
                  stroke={C_RULE}
                  strokeWidth={0.7 / t.k}
                  strokeLinejoin="round"
                />
              </g>
              {baseDots}
              {/* Pinned: concentric ink ring that persists until you click
                  elsewhere (matches the VAM/VAC sticky highlight). */}
              {pinnedPoint && (
                <g pointerEvents="none">
                  <circle cx={pinnedPoint.x} cy={pinnedPoint.y} r={8 / t.k} fill="none" stroke={C_INK} strokeWidth={2 / t.k} />
                  <circle
                    cx={pinnedPoint.x}
                    cy={pinnedPoint.y}
                    r={3 / t.k}
                    fill={scale ? scale.color(pinnedPoint.value) : C_INK}
                    stroke={C_INK}
                    strokeWidth={1 / t.k}
                  />
                </g>
              )}
              {/* Hovered: transient teal ring, drawn on top of a pin if any. */}
              {hoveredPoint && (
                <circle
                  cx={hoveredPoint.x}
                  cy={hoveredPoint.y}
                  r={6.5 / t.k}
                  fill="none"
                  stroke="#0c6b61"
                  strokeWidth={1.6 / t.k}
                  pointerEvents="none"
                />
              )}
            </g>
          </svg>

          {/* Pinned tooltip: interactive (name links to College Navigator, ×
              dismisses), persists while you hover other dots. */}
          {pinnedPoint && (
            <Tooltip
              point={pinnedPoint}
              kind={variable.kind}
              label={variable.label}
              transform={t}
              interactive
              onClose={() => setPinned(null)}
            />
          )}
          {/* Hover tooltip: transient preview for a different dot. */}
          {hoveredPoint && (
            <Tooltip
              point={hoveredPoint}
              kind={variable.kind}
              label={variable.label}
              transform={t}
              interactive={false}
            />
          )}
        </div>
      </section>
    </div>
  );
}

/** Floating tooltip anchored to the active dot's projected position (as % of viewBox). */
function Tooltip({
  point,
  kind,
  label,
  transform,
  interactive,
  onClose,
}: {
  point: PlottedPoint;
  kind: typeof VARIABLES[VariableId]["kind"];
  label: string;
  transform: { k: number; tx: number; ty: number };
  interactive: boolean;
  onClose?: () => void;
}) {
  // Anchor to the dot's on-screen position after the zoom/pan transform.
  const sx = point.x * transform.k + transform.tx;
  const sy = point.y * transform.k + transform.ty;
  const leftPct = (sx / WIDTH) * 100;
  const topPct = (sy / HEIGHT) * 100;
  const place = point.city && point.state ? `${point.city}, ${point.state}` : point.state ?? point.city ?? "";
  return (
    <div
      className={`absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+10px)] rounded-md border bg-panel px-3 py-2 shadow-sm ${
        interactive ? "pointer-events-auto border-ink/40 pr-6" : "pointer-events-none border-rule"
      }`}
      style={{ left: `${leftPct}%`, top: `${topPct}%` }}
      onPointerDown={interactive ? (e) => e.stopPropagation() : undefined}
    >
      {interactive && onClose && (
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
        {interactive ? <CollegeNavLink unitid={point.unitid} name={point.name} /> : point.name}
      </p>
      {place && (
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft">{place}</p>
      )}
      <p className="mt-1 whitespace-nowrap font-mono text-xs tabular-nums text-ink-soft">
        {label}: <span className="text-ink">{formatMetric(point.value, kind)}</span>
      </p>
    </div>
  );
}

/** Duotone color-scale legend with min / median / max ticks. */
function Legend({
  scale,
  kind,
  diverging,
  reverse,
}: {
  scale: NonNullable<ReturnType<typeof buildColorScale>>;
  kind: typeof VARIABLES[VariableId]["kind"];
  diverging: boolean;
  reverse: boolean;
}) {
  // Sample the ramp across the value domain so the bar matches the dot colors.
  const stops = useMemo(() => {
    const n = 24;
    return Array.from({ length: n }, (_, i) => {
      const v = scale.min + ((scale.max - scale.min) * i) / (n - 1);
      return scale.color(v);
    });
  }, [scale]);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="flex items-center gap-3">
        <div
          className="h-2.5 w-40 rounded-full"
          style={{ background: `linear-gradient(to right, ${stops.join(",")})` }}
        />
      </div>
      <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft tabular-nums">
        <span>min {formatMetric(scale.min, kind)}</span>
        {diverging && <span>median {formatMetric(scale.med, kind)}</span>}
        <span>max {formatMetric(scale.max, kind)}</span>
        {reverse && <span className="text-ink-soft/70">(lower = warmer)</span>}
      </div>
    </div>
  );
}
