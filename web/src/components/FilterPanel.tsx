"use client";

import Select from "@/components/Select";
import MultiSelect from "@/components/MultiSelect";
import type { FilterDef, FilterState } from "@/lib/filters";

/**
 * Declarative filter panel — replaces the legacy magic-number onclick filters.
 *
 * Contract: pass `defs` (FilterDef[]) describing the filters as data, the
 * current `state`, and an `onChange`. The panel renders the appropriate control
 * per def kind. Use `applyFilters(rows, defs, state)` from @/lib/filters to run
 * them. No filter is hard-coded; tools declare filters as config.
 */
export interface FilterPanelProps {
  defs: FilterDef[];
  state: FilterState;
  onChange: (next: FilterState) => void;
  onReset?: () => void;
}

export default function FilterPanel({ defs, state, onChange, onReset }: FilterPanelProps) {
  function set(id: string, value: FilterState[string]) {
    onChange({ ...state, [id]: value });
  }

  return (
    <div className="h-full space-y-4 rounded-lg border border-rule bg-panel p-4">
      <div className="flex items-center justify-between border-b border-rule pb-3">
        <h3 className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          Filters
        </h3>
        {onReset && (
          <button
            onClick={onReset}
            className="font-mono text-[11px] uppercase tracking-[0.12em] text-teal transition-colors hover:text-teal-bright"
          >
            Reset
          </button>
        )}
      </div>

      {defs.map((def) => (
        <div key={def.id} className="space-y-1.5">
          <label className="block font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">
            {def.label}
          </label>

          {def.kind === "select" && def.multi && (
            <MultiSelect
              ariaLabel={def.label}
              values={(state[def.id] as string[] | undefined) ?? []}
              onChange={(vals) => set(def.id, vals.length ? vals : undefined)}
              placeholder="All"
              options={def.options.map((o) => ({ label: o.label, value: String(o.value) }))}
              groups={def.optionGroups}
            />
          )}

          {def.kind === "select" && !def.multi && (
            <Select
              ariaLabel={def.label}
              value={(state[def.id] as string | number | undefined)?.toString() ?? ""}
              onChange={(v) => set(def.id, v === "" ? undefined : v)}
              placeholder="All"
              options={[
                ...(def.required ? [] : [{ label: "All", value: "" }]),
                ...def.options.map((o) => ({ label: o.label, value: String(o.value) })),
              ]}
            />
          )}

          {def.kind === "toggle" && (
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={state[def.id] === true}
                onChange={(e) => set(def.id, e.target.checked || undefined)}
                className="accent-teal"
              />
              Only show matching
            </label>
          )}

          {def.kind === "range" && (
            <RangeControl def={def} value={state[def.id] as [number, number] | undefined} onChange={(v) => set(def.id, v)} />
          )}
        </div>
      ))}
    </div>
  );
}

function RangeControl({
  def,
  value,
  onChange,
}: {
  def: Extract<FilterDef, { kind: "range" }>;
  value: [number, number] | undefined;
  onChange: (v: [number, number] | undefined) => void;
}) {
  // Bounds aren't known until the data loads (min===max as a sentinel). Show a
  // muted placeholder rather than flashing "1 to 1" → "1 to 395".
  const ready = def.max > def.min;
  const [lo, hi] = value ?? [def.min, def.max];
  const inputCls =
    "min-w-0 flex-1 rounded-md border border-rule bg-paper px-2 py-1 text-sm tabular-nums text-ink outline-none transition-colors focus:border-teal focus:ring-1 focus:ring-teal/30 disabled:opacity-50";
  if (!ready) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft/60">
        Loading range…
      </p>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <input
        type="number"
        inputMode="numeric"
        value={lo}
        min={def.min}
        max={def.max}
        step={def.step}
        onChange={(e) => onChange([Number(e.target.value), hi])}
        className={inputCls}
      />
      <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft">to</span>
      <input
        type="number"
        inputMode="numeric"
        value={hi}
        min={def.min}
        max={def.max}
        step={def.step}
        onChange={(e) => onChange([lo, Number(e.target.value)])}
        className={inputCls}
      />
    </div>
  );
}
