"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Checkbox multi-select popover, styled to match `Select`. Several options can
 * be chosen at once; the trigger summarizes the selection ("All", the single
 * label, or "N selected"). A search box appears when the list is long. Used by
 * FilterPanel for `multi` select filters (e.g. State).
 */
export interface MultiSelectOption {
  label: string;
  value: string;
}

export interface MultiSelectGroup {
  label: string;
  options: MultiSelectOption[];
}

interface Props {
  values: string[];
  onChange: (values: string[]) => void;
  options: MultiSelectOption[];
  /** Optional grouped presentation (headers). `options` remains the flat union. */
  groups?: MultiSelectGroup[];
  placeholder?: string;
  ariaLabel?: string;
  className?: string;
}

export default function MultiSelect({
  values,
  onChange,
  options,
  groups,
  placeholder = "All",
  ariaLabel,
  className = "",
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement | null>(null);

  const selectedSet = useMemo(() => new Set(values), [values]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (value: string) => {
    onChange(
      selectedSet.has(value) ? values.filter((v) => v !== value) : [...values, value],
    );
  };

  const label =
    values.length === 0
      ? placeholder
      : values.length === 1
        ? options.find((o) => o.value === values[0])?.label ?? values[0]
        : `${values.length} selected`;

  const q = query.trim().toLowerCase();
  const match = (o: MultiSelectOption) => !q || o.label.toLowerCase().includes(q);
  const shown = options.filter(match);
  // Grouped view: keep only groups with a surviving option after search.
  const shownGroups = (groups ?? [])
    .map((g) => ({ label: g.label, options: g.options.filter(match) }))
    .filter((g) => g.options.length > 0);

  const renderOption = (o: MultiSelectOption) => {
    const checked = selectedSet.has(o.value);
    return (
      <li key={o.value}>
        <button
          type="button"
          role="option"
          aria-selected={checked}
          onClick={() => toggle(o.value)}
          className={[
            "flex w-full cursor-pointer items-center gap-2 px-2.5 py-1.5 text-left text-sm transition-colors",
            checked ? "text-ink" : "text-ink-soft",
            "hover:bg-paper-2",
          ].join(" ")}
        >
          <span
            aria-hidden
            className={`grid h-3.5 w-3.5 shrink-0 place-items-center rounded-sm border transition-colors ${
              checked ? "border-teal bg-teal text-paper" : "border-rule bg-paper"
            }`}
          >
            {checked && (
              <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden>
                <path d="M1 5l2.5 3L9 1.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </span>
          <span className="whitespace-nowrap">{o.label}</span>
        </button>
      </li>
    );
  };

  // Toggle every option in a group on/off (e.g. select a whole region's states).
  const toggleGroup = (opts: MultiSelectOption[]) => {
    const vals = opts.map((o) => o.value);
    const allOn = vals.every((v) => selectedSet.has(v));
    onChange(allOn ? values.filter((v) => !vals.includes(v)) : [...new Set([...values, ...vals])]);
  };

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-md border border-rule bg-paper px-2.5 py-1.5 text-left text-sm text-ink outline-none transition-colors hover:border-ink-soft focus:border-teal focus:ring-1 focus:ring-teal/30"
      >
        <span className={`truncate ${values.length ? "text-ink" : "text-ink-soft/70"}`}>{label}</span>
        <svg
          width="10"
          height="6"
          viewBox="0 0 10 6"
          aria-hidden
          className={`shrink-0 text-ink-soft transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-30 mt-1 min-w-full w-max max-w-[min(24rem,80vw)] rounded-md border border-rule bg-panel py-1 shadow-lg">
          {options.length > 8 && (
            <div className="px-2 pb-1 pt-0.5">
              <input
                type="search"
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search…"
                className="w-full rounded border border-rule bg-paper px-2 py-1 text-sm text-ink outline-none placeholder:text-ink-soft/60 focus:border-teal"
              />
            </div>
          )}
          {values.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="w-full px-2.5 py-1 text-left font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft transition-colors hover:text-oxblood"
            >
              Clear selection
            </button>
          )}
          <ul role="listbox" aria-multiselectable className="max-h-56 overflow-auto">
            {groups
              ? shownGroups.map((g) => {
                  const allOn = g.options.every((o) => selectedSet.has(o.value));
                  return (
                    <li key={g.label}>
                      <button
                        type="button"
                        onClick={() => toggleGroup(g.options)}
                        title={allOn ? `Deselect all in ${g.label}` : `Select all in ${g.label}`}
                        className="flex w-full items-center justify-between gap-2 px-2.5 pb-0.5 pt-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-soft/70 transition-colors hover:text-teal"
                      >
                        {g.label}
                        <span aria-hidden>{allOn ? "clear" : "all"}</span>
                      </button>
                      <ul>{g.options.map(renderOption)}</ul>
                    </li>
                  );
                })
              : shown.map(renderOption)}
            {(groups ? shownGroups.length === 0 : shown.length === 0) && (
              <li className="px-2.5 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft/70">
                No matches
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
