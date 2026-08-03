"use client";

import type { HTMLAttributes, ReactElement, ReactNode, Ref } from "react";
import { ResponsiveContainer } from "recharts";

/**
 * Reusable chart chrome + sizing wrapper, shared by all tools.
 *
 * Contract:
 *  - <ChartCard> renders the titled card (header with title/subtitle + optional
 *    actions slot) and a responsive, fixed-height plot area.
 *  - `children` must be a SINGLE Recharts chart element (LineChart, ScatterChart,
 *    BarChart, …) — it is handed straight to Recharts' ResponsiveContainer.
 *
 * This keeps every tool visually consistent and lets the next tools (VAM/VAC
 * scatter, etc.) drop in their own Recharts chart without re-implementing
 * layout or sizing.
 */
export interface ChartCardProps {
  title?: string;
  subtitle?: string;
  /** Right-aligned actions in the header (e.g. Clear/Reset buttons). */
  actions?: ReactNode;
  /** Optional custom legend, rendered OUTSIDE the SVG so it wraps cleanly. */
  legend?: ReactNode;
  /** Plot height in px. */
  height?: number;
  /** Optional ref to the plot area (e.g. for attaching a wheel/zoom listener). */
  plotRef?: Ref<HTMLDivElement>;
  /** Optional props spread onto the plot area (e.g. pointer handlers for pan). */
  plotProps?: HTMLAttributes<HTMLDivElement>;
  /** Absolutely-positioned layer over the plot (pointer-events-none), e.g. a
   *  hover highlight that must NOT live inside the memoized chart. */
  overlay?: ReactNode;
  /** Exactly one Recharts chart element. */
  children: ReactElement;
}

export default function ChartCard({
  title,
  subtitle,
  actions,
  legend,
  height = 440,
  plotRef,
  plotProps,
  overlay,
  children,
}: ChartCardProps) {
  const { className: plotClassName, ...plotRest } = plotProps ?? {};
  return (
    <section className="flex h-full flex-col rounded-lg border border-rule bg-panel">
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-rule px-6 py-4">
          <div>
            {title && (
              <h2 className="font-display text-lg font-semibold tracking-tight text-ink">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      {legend && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-rule px-6 py-3">
          {legend}
        </div>
      )}
      <div
        ref={plotRef}
        className={`relative min-h-0 flex-1 px-3 py-5 ${plotClassName ?? ""}`}
        style={{ minHeight: height }}
        {...plotRest}
      >
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
        {/* inset-0 matches plotRef's box (no border on this div), so the tool
            can position overlay content with the same INSET used for pan/zoom. */}
        {overlay != null && (
          <div className="pointer-events-none absolute inset-0">{overlay}</div>
        )}
      </div>
    </section>
  );
}
