"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Styled select that matches the app's form controls — the native <select>
 * pop-up list can't be themed cross-browser, so this renders a paper-styled
 * trigger + custom option list (click-outside + Escape to close, arrow keys to
 * move, Enter to choose). Optional `groups` render labeled sections.
 */
export interface SelectOption {
  label: string;
  value: string;
}
export interface SelectGroup {
  label: string;
  options: SelectOption[];
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  options?: SelectOption[];
  groups?: SelectGroup[];
  placeholder?: string;
  ariaLabel?: string;
  className?: string;
}

export default function Select({
  value,
  onChange,
  options,
  groups,
  placeholder = "Select…",
  ariaLabel,
  className = "",
}: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement | null>(null);

  const flat: SelectOption[] = groups ? groups.flatMap((g) => g.options) : options ?? [];
  const current = flat.find((o) => o.value === value);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => Math.min(flat.length - 1, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => Math.max(0, i - 1));
      } else if (e.key === "Enter" && flat[active]) {
        e.preventDefault();
        onChange(flat[active].value);
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, flat, active, onChange]);

  const openList = () => {
    const idx = flat.findIndex((o) => o.value === value);
    setActive(idx < 0 ? 0 : idx);
    setOpen((v) => !v);
  };

  function renderOption(o: SelectOption, idx: number) {
    const isActive = idx === active;
    const isSelected = o.value === value;
    return (
      <li key={o.value}>
        <button
          type="button"
          role="option"
          aria-selected={isSelected}
          onMouseEnter={() => setActive(idx)}
          onClick={() => {
            onChange(o.value);
            setOpen(false);
          }}
          className={[
            "flex w-full cursor-pointer items-center justify-between gap-2 px-2.5 py-1.5 text-left text-sm transition-colors",
            isActive ? "bg-paper-2 text-ink" : "text-ink-soft",
            isSelected ? "font-medium text-ink" : "",
          ].join(" ")}
        >
          <span className="whitespace-nowrap">{o.label}</span>
          {isSelected && <span className="shrink-0 text-teal">✓</span>}
        </button>
      </li>
    );
  }

  let counter = -1;
  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={openList}
        className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-md border border-rule bg-paper px-2.5 py-1.5 text-left text-sm text-ink outline-none transition-colors hover:border-ink-soft focus:border-teal focus:ring-1 focus:ring-teal/30"
      >
        <span className={`truncate ${current ? "text-ink" : "text-ink-soft/70"}`}>
          {current ? current.label : placeholder}
        </span>
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
        <ul
          role="listbox"
          // `w-max` lets the open list grow to its longest option (so long
          // labels aren't clipped), `min-w-full` keeps it at least as wide as
          // the trigger, and `max-w` caps it so it can't overrun the viewport.
          className="absolute z-30 mt-1 max-h-64 min-w-full w-max max-w-[min(24rem,80vw)] overflow-auto rounded-md border border-rule bg-panel py-1 shadow-lg"
        >
          {groups
            ? groups.map((g) => (
                <li key={g.label}>
                  <p className="px-2.5 pb-0.5 pt-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-soft/70">
                    {g.label}
                  </p>
                  <ul>{g.options.map((o) => renderOption(o, ++counter))}</ul>
                </li>
              ))
            : (options ?? []).map((o) => renderOption(o, ++counter))}
        </ul>
      )}
    </div>
  );
}
