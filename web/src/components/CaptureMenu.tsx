"use client";

// TEMP — see src/lib/capture.ts. Hidden capture controller + menu.
// Type the unlock word ("grey") anywhere (outside a text field) to reveal it.
// It arms capture mode (export buttons appear on chart cards) and switches the
// site-wide greyscale look. State is mirrored onto <html> (data-grey /
// data-capture-on) and persisted in localStorage.

import { useEffect, useState } from "react";
import {
  MODES,
  MODE_KEY,
  ARMED_KEY,
  UNLOCK_WORD,
  isGreyMode,
  type GreyMode,
} from "@/lib/capture";

export default function CaptureMenu() {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<GreyMode>("off");

  // Restore persisted state on mount and reflect it onto <html>.
  useEffect(() => {
    const saved = localStorage.getItem(MODE_KEY);
    const armed = localStorage.getItem(ARMED_KEY) === "1";
    const m: GreyMode = isGreyMode(saved) ? saved : "off";
    setMode(m);
    document.documentElement.dataset.grey = m;
    if (armed) document.documentElement.setAttribute("data-capture-on", "");
  }, []);

  // Listen for the typed unlock word.
  useEffect(() => {
    let buf = "";
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      if (e.key === "Escape") {
        setOpen(false);
        return;
      }
      if (e.key.length !== 1) return;
      buf = (buf + e.key.toLowerCase()).slice(-UNLOCK_WORD.length);
      if (buf === UNLOCK_WORD) {
        buf = "";
        document.documentElement.setAttribute("data-capture-on", "");
        localStorage.setItem(ARMED_KEY, "1");
        setOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function apply(m: GreyMode) {
    setMode(m);
    document.documentElement.dataset.grey = m;
    localStorage.setItem(MODE_KEY, m);
  }

  function disable() {
    apply("off");
    document.documentElement.removeAttribute("data-capture-on");
    localStorage.removeItem(ARMED_KEY);
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div
      data-export-ignore
      // Inline position/z-index: the global `.grain > *` rule (globals.css)
      // sets position:relative + z-index:1 on every direct <body> child, which
      // would otherwise override the Tailwind `fixed`/`z-` utilities here.
      style={{ position: "fixed", zIndex: 60 }}
      className="bottom-5 right-5 w-72 overflow-hidden rounded-xl border border-rule bg-panel shadow-[0_16px_40px_-12px_rgba(27,36,48,0.45)]"
    >
      <div className="flex items-center justify-between border-b border-rule px-4 py-2.5">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft">
          Capture · greyscale
        </span>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="font-mono text-[13px] leading-none text-ink-soft transition-colors hover:text-ink"
          aria-label="Close capture menu"
        >
          ✕
        </button>
      </div>

      <div className="px-4 py-3">
        <div className="grid grid-cols-1 gap-1.5">
          {MODES.map((m) => {
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => apply(m.id)}
                className={[
                  "flex items-center justify-between rounded-md border px-3 py-2 text-left transition-colors",
                  active
                    ? "border-teal bg-teal/10 text-ink"
                    : "border-rule text-ink-soft hover:border-ink/30 hover:text-ink",
                ].join(" ")}
              >
                <span className="font-mono text-[12px] uppercase tracking-[0.12em]">
                  {m.label}
                </span>
                <span className="font-sans text-[11px] text-ink-soft">{m.hint}</span>
              </button>
            );
          })}
        </div>

        <p className="mt-3 font-sans text-[11px] leading-snug text-ink-soft">
          Hover any chart and click <span className="text-ink">Export PNG</span> to
          save it at 3&times; resolution.
        </p>

        <button
          type="button"
          onClick={disable}
          className="mt-3 w-full rounded-md border border-rule py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-soft transition-colors hover:border-oxblood hover:text-oxblood"
        >
          Disable capture
        </button>
      </div>
    </div>
  );
}
