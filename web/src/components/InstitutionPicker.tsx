"use client";

import { useMemo, useState } from "react";
import { collegeNavigatorUrl } from "@/lib/links";

/** Minimal shape the picker needs; both Institution and RetentionInstitution satisfy it. */
export interface PickerItem {
  unitid: number;
  name: string;
  region?: string | null;
  state?: string | null;
  national?: boolean | null;
  usNewsRank?: number | null;
}

interface Props {
  items: PickerItem[];
  /** Selected unitids, in selection order. */
  selected: number[];
  onToggle: (unitid: number) => void;
  onClear?: () => void;
  /** Stable color for a unitid's swatch (only shown for selected rows). */
  colorFor?: (unitid: number) => string;
  /** Cross-highlight: the row currently hovered (drives the chart). */
  hovered?: number | null;
  onHover?: (unitid: number | null) => void;
  loading?: boolean;
  /** Verb for the header count, e.g. "selected" or "highlighted". */
  verb?: string;
  className?: string;
}

const CAP = 100;


export default function InstitutionPicker({
  items,
  selected,
  onToggle,
  onClear,
  colorFor,
  hovered,
  onHover,
  loading,
  verb = "selected",
  className = "",
}: Props) {
  const [query, setQuery] = useState("");

  const selSet = useMemo(() => new Set(selected), [selected]);

  // The pick-list is a find-and-highlight aid; the left filter panel already
  // narrows the plot (classification / control / region / rank). So this list
  // filters on the search box ONLY — no duplicate classification/region/rank
  // controls, which previously read as graph filters and confused users.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out = items.filter((i) => !q || i.name.toLowerCase().includes(q));
    // selected first (selection order), then alphabetical
    const order = new Map(selected.map((id, idx) => [id, idx]));
    out.sort((a, b) => {
      const sa = order.has(a.unitid);
      const sb = order.has(b.unitid);
      if (sa && sb) return order.get(a.unitid)! - order.get(b.unitid)!;
      if (sa) return -1;
      if (sb) return 1;
      return a.name.localeCompare(b.name);
    });
    return out;
  }, [items, query, selected]);

  const visible = filtered.slice(0, CAP);
  const overflow = filtered.length - visible.length;
  const selectedItems = selected
    .map((id) => items.find((i) => i.unitid === id))
    .filter(Boolean) as PickerItem[];

  return (
    <aside
      // Fixed height when stacked (mobile); on lg the grid stretches it to the
      // chart's height. `overflow-hidden` + the absolutely-positioned scroll
      // list below means the 100-row list never inflates this panel (which
      // previously dragged the whole chart to thousands of px tall).
      className={`relative flex h-[520px] flex-col overflow-hidden rounded-lg border border-rule bg-panel lg:h-auto ${className}`}
    >
      {/* selected chips */}
      {selectedItems.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b border-rule p-3">
          <span className="mr-1 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-soft">
            {selectedItems.length} {verb}
          </span>
          {selectedItems.map((i) => (
            <button
              key={i.unitid}
              onClick={() => onToggle(i.unitid)}
              className="group inline-flex max-w-[150px] items-center gap-1 rounded-full border border-rule bg-paper py-0.5 pl-1.5 pr-2 text-[11px] text-ink transition-colors hover:border-teal"
              title={`Remove ${i.name}`}
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: colorFor?.(i.unitid) ?? "var(--color-teal)" }}
              />
              <span className="truncate">{i.name}</span>
              <span className="text-ink-soft transition-colors group-hover:text-oxblood">
                &times;
              </span>
            </button>
          ))}
          {onClear && (
            <button
              onClick={onClear}
              className="ml-auto font-mono text-[10px] uppercase tracking-[0.14em] text-ink-soft transition-colors hover:text-oxblood"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* search */}
      <div className="border-b border-rule p-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search to highlight universities…"
          className="w-full rounded-md border border-rule bg-paper px-3 py-1.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-soft/60 focus:border-teal focus:ring-1 focus:ring-teal/30"
        />
      </div>

      {/* list — the flex-1 wrapper reserves space; the scroll list is absolute
          so its content height never feeds back into the panel/grid height. */}
      <div className="relative min-h-0 flex-1">
      <div className="absolute inset-0 overflow-y-auto p-1.5" onMouseLeave={() => onHover?.(null)}>
        {loading && (
          <p className="p-3 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            Loading universities…
          </p>
        )}
        {!loading && filtered.length === 0 && (
          <p className="p-3 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            No matches
          </p>
        )}
        {visible.map((i) => {
          const isSel = selSet.has(i.unitid);
          const isHover = hovered === i.unitid;
          return (
            <div
              key={i.unitid}
              onMouseEnter={() => onHover?.(i.unitid)}
              className={[
                "group flex w-full items-center gap-1 rounded-md pr-1 text-left text-sm transition-colors",
                isSel || isHover ? "bg-paper" : "hover:bg-paper",
              ].join(" ")}
            >
              {/* The row body toggles highlight; the name links out separately
                  (a ↗ affordance) so a click still selects, matching the chart. */}
              <button
                onClick={() => onToggle(i.unitid)}
                className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-2 py-1.5 text-left"
              >
                <span
                  className="inline-block h-3 w-3 shrink-0 rounded-full border border-rule transition-colors"
                  style={{
                    background: isSel
                      ? (colorFor?.(i.unitid) ?? "var(--color-teal)")
                      : "transparent",
                  }}
                  aria-hidden
                />
                <span className={`truncate ${isSel ? "font-medium text-ink" : "text-ink-soft"}`}>
                  {i.name}
                </span>
                {(i.state || i.region) && (
                  <span className="ml-auto shrink-0 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-soft/60">
                    {i.state ?? i.region}
                  </span>
                )}
              </button>
              <a
                href={collegeNavigatorUrl(i.unitid)}
                target="_blank"
                rel="noopener noreferrer"
                title={`${i.name} — open on College Navigator ↗`}
                className="shrink-0 rounded px-1 py-0.5 font-mono text-[11px] leading-none text-ink-soft/40 opacity-0 transition-colors hover:text-teal focus:opacity-100 group-hover:opacity-100"
              >
                ↗
              </a>
            </div>
          );
        })}
        {overflow > 0 && (
          <p className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft/70">
            Showing {visible.length} of {filtered.length} — refine to see more
          </p>
        )}
      </div>
      </div>
    </aside>
  );
}
