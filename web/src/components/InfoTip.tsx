"use client";

import { useState, type ReactNode } from "react";

/**
 * Lightweight hover/focus tooltip. The native `title` attribute only shows the
 * browser's slow, unstyled tooltip (and nothing on touch), so this renders an
 * immediate, styled popover instead. `children` is the trigger; `tip` is the
 * popover content.
 */
export default function InfoTip({
  children,
  tip,
  className = "",
}: {
  children: ReactNode;
  tip: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className={`relative inline-flex ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      tabIndex={0}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          className="absolute left-0 top-full z-40 mt-2 w-64 rounded-md border border-rule bg-panel px-3 py-2 text-[11px] font-normal normal-case leading-relaxed tracking-normal text-ink-soft shadow-lg"
        >
          {tip}
        </span>
      )}
    </span>
  );
}
