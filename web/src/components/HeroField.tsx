"use client";

import { useEffect, useRef } from "react";

/**
 * The hero's signature visual: a drifting constellation of "institutions"
 * (dots) with hairline connections and gentle mouse parallax. Foreshadows the
 * future map view. Canvas-based, DPR-aware, and honours reduced-motion.
 */
export default function HeroField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const INK = "27, 36, 48";
    const TEAL = "12, 107, 97";
    const OCHRE = "224, 165, 59";

    let w = 0;
    let h = 0;
    let dpr = 1;
    const mouse = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };

    type Node = {
      x: number;
      y: number;
      vx: number;
      vy: number;
      r: number;
      depth: number; // 0..1 — parallax + size
      hue: "ink" | "teal" | "ochre";
      tw: number; // twinkle phase
    };
    let nodes: Node[] = [];

    function rand(a: number, b: number) {
      // deterministic-enough jitter without Math.random dependency concerns
      return a + (b - a) * Math.abs(Math.sin((seed += 0.6180339) * 9973) % 1);
    }
    let seed = 7.13;

    function build() {
      const count = Math.max(46, Math.min(120, Math.round((w * h) / 13000)));
      nodes = Array.from({ length: count }, () => {
        const depth = rand(0, 1);
        const hueRoll = rand(0, 1);
        return {
          x: rand(0, w),
          y: rand(0, h),
          vx: (rand(-1, 1) * 0.12) / 1,
          vy: (rand(-1, 1) * 0.12) / 1,
          r: 0.8 + depth * 2.4,
          depth,
          hue: hueRoll > 0.86 ? "ochre" : hueRoll > 0.62 ? "teal" : "ink",
          tw: rand(0, Math.PI * 2),
        };
      });
    }

    function resize() {
      const rect = canvas!.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = rect.width;
      h = rect.height;
      canvas!.width = Math.round(w * dpr);
      canvas!.height = Math.round(h * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
    }

    let raf = 0;
    let t = 0;
    function frame() {
      t += 1;
      mouse.x += (mouse.tx - mouse.x) * 0.05;
      mouse.y += (mouse.ty - mouse.y) * 0.05;
      const px = (mouse.x - 0.5) * 26;
      const py = (mouse.y - 0.5) * 26;

      ctx!.clearRect(0, 0, w, h);

      // connections (hairline constellation)
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        const ax = a.x + px * a.depth;
        const ay = a.y + py * a.depth;
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const bx = b.x + px * b.depth;
          const by = b.y + py * b.depth;
          const dx = ax - bx;
          const dy = ay - by;
          const d2 = dx * dx + dy * dy;
          if (d2 < 118 * 118) {
            const alpha = (1 - Math.sqrt(d2) / 118) * 0.16;
            ctx!.strokeStyle = `rgba(${INK}, ${alpha})`;
            ctx!.lineWidth = 0.6;
            ctx!.beginPath();
            ctx!.moveTo(ax, ay);
            ctx!.lineTo(bx, by);
            ctx!.stroke();
          }
        }
      }

      // nodes
      for (const n of nodes) {
        if (!reduce) {
          n.x += n.vx;
          n.y += n.vy;
          if (n.x < -4) n.x = w + 4;
          if (n.x > w + 4) n.x = -4;
          if (n.y < -4) n.y = h + 4;
          if (n.y > h + 4) n.y = -4;
        }
        const twinkle = 0.55 + 0.45 * Math.sin(t * 0.02 + n.tw);
        const col = n.hue === "teal" ? TEAL : n.hue === "ochre" ? OCHRE : INK;
        const a = (0.22 + n.depth * 0.5) * (reduce ? 1 : twinkle);
        ctx!.fillStyle = `rgba(${col}, ${a})`;
        ctx!.beginPath();
        ctx!.arc(n.x + px * n.depth, n.y + py * n.depth, n.r, 0, Math.PI * 2);
        ctx!.fill();
        if (n.hue !== "ink" && n.depth > 0.7) {
          ctx!.strokeStyle = `rgba(${col}, ${a * 0.5})`;
          ctx!.lineWidth = 0.8;
          ctx!.beginPath();
          ctx!.arc(
            n.x + px * n.depth,
            n.y + py * n.depth,
            n.r + 3.5,
            0,
            Math.PI * 2,
          );
          ctx!.stroke();
        }
      }

      raf = requestAnimationFrame(frame);
    }

    function onMove(e: PointerEvent) {
      const rect = canvas!.getBoundingClientRect();
      mouse.tx = (e.clientX - rect.left) / rect.width;
      mouse.ty = (e.clientY - rect.top) / rect.height;
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove);
    if (reduce) {
      frame();
      cancelAnimationFrame(raf);
      frame(); // one static paint
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="absolute inset-0 h-full w-full"
    />
  );
}
