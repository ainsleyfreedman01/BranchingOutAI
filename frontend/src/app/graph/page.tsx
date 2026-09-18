"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

function GraphContent() {
  const { user, signOut, loading } = useAuth();
  const router = useRouter();
  const [helpOpen, setHelpOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const paperRef = useRef<import("@joint/core").dia.Paper | null>(null);

  // Smooth zoom state — target scale animates toward via RAF
  const targetScaleRef = useRef<number | null>(null);
  const zoomRafRef = useRef<number | null>(null);
  const zoomOriginRef = useRef<{ ox: number; oy: number } | null>(null);

  const animateToScale = useCallback((targetScale: number, ox: number, oy: number) => {
    targetScaleRef.current = Math.min(3, Math.max(0.2, targetScale));
    zoomOriginRef.current = { ox, oy };
    if (zoomRafRef.current !== null) return; // already animating
    const step = () => {
      const paper = paperRef.current;
      if (!paper || targetScaleRef.current === null) { zoomRafRef.current = null; return; }
      const current = paper.scale().sx;
      const target = targetScaleRef.current;
      const diff = target - current;
      if (Math.abs(diff) < 0.001) {
        paper.scale(target, target);
        zoomRafRef.current = null;
        targetScaleRef.current = null;
        return;
      }
      const next = current + diff * 0.18; // easing factor
      const { ox: originX, oy: originY } = zoomOriginRef.current!;
      const t = paper.translate();
      const newTx = originX - (originX - t.tx) * (next / current);
      const newTy = originY - (originY - t.ty) * (next / current);
      paper.scale(next, next);
      paper.translate(newTx, newTy);
      zoomRafRef.current = requestAnimationFrame(step);
    };
    zoomRafRef.current = requestAnimationFrame(step);
  }, []);

  const zoom = useCallback((factor: number) => {
    const paper = paperRef.current;
    if (!paper) return;
    const current = targetScaleRef.current ?? paper.scale().sx;
    const svgEl = paper.el as HTMLElement;
    const rect = svgEl.getBoundingClientRect();
    const ox = rect.width / 2;
    const oy = rect.height / 2;
    animateToScale(current * factor, ox, oy);
  }, [animateToScale]);

  const resetView = useCallback(() => {
    const paper = paperRef.current;
    if (!paper) return;
    const svgEl = paper.el as HTMLElement;
    const rect = svgEl.getBoundingClientRect();
    animateToScale(1, rect.width / 2, rect.height / 2);
    // Also animate translation back to 0,0
    const startTx = paper.translate().tx;
    const startTy = paper.translate().ty;
    let start: number | null = null;
    const panBack = (ts: number) => {
      if (start === null) start = ts;
      const p = Math.min((ts - start) / 200, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      paper.translate(startTx * (1 - ease), startTy * (1 - ease));
      if (p < 1) requestAnimationFrame(panBack);
    };
    requestAnimationFrame(panBack);
  }, [animateToScale]);

  // Redirect to home if not logged in
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  // Initialize JointJS canvas
  useEffect(() => {
    if (!user || !containerRef.current) return;

    let cancelled = false;
    let cleanup: (() => void) | undefined;

    (async () => {
      const { dia, shapes } = await import("@joint/core");
      if (cancelled || !containerRef.current) return;

      const graph = new dia.Graph({}, { cellNamespace: shapes });

      const containerEl = containerRef.current!;
      const paperEl = document.createElement("div");
      paperEl.style.height = "100%";
      paperEl.style.width = "100%";
      containerEl.appendChild(paperEl);
      const w = containerEl.clientWidth || 800;
      const h = containerEl.clientHeight || 600;

      const paper = new dia.Paper({
        el: paperEl,
        model: graph,
        width: "100%",
        height: "100%",
        gridSize: 10,
        drawGrid: { name: "mesh", args: { color: "#dcfce7", thickness: 1 } },
        background: { color: "#f7fdf9" },
        cellViewNamespace: shapes,
        interactive: true,
        // Infinite canvas — allow panning beyond the initial viewport
        overflow: true,
      });

      paperRef.current = paper;

      const svgEl = paper.el as HTMLElement;
      svgEl.style.cursor = "move";

      // Pan on left-click drag on the blank paper background
      let isPanning = false;
      let panStart = { x: 0, y: 0 };
      let translateStart = { tx: 0, ty: 0 };

      paper.on("blank:pointerdown", (evt: object) => {
        const e = evt as MouseEvent;
        isPanning = true;
        panStart = { x: e.clientX, y: e.clientY };
        const t = paper.translate();
        translateStart = { tx: t.tx, ty: t.ty };
        svgEl.style.cursor = "grabbing";
      });

      const onMouseMove = (e: MouseEvent) => {
        if (!isPanning) return;
        const dx = e.clientX - panStart.x;
        const dy = e.clientY - panStart.y;
        paper.translate(translateStart.tx + dx, translateStart.ty + dy);
      };
      const onMouseUp = () => {
        isPanning = false;
        svgEl.style.cursor = "move";
      };
      const onContextMenu = (e: Event) => e.preventDefault();

      // Scroll-wheel zoom — accumulate target scale and animate via RAF
      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
        const current = targetScaleRef.current ?? paper.scale().sx;
        const rect = svgEl.getBoundingClientRect();
        const ox = e.clientX - rect.left;
        const oy = e.clientY - rect.top;
        animateToScale(current * factor, ox, oy);
      };

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      svgEl.addEventListener("contextmenu", onContextMenu);
      svgEl.addEventListener("wheel", onWheel, { passive: false });

      const firstName = (user.user_metadata?.first_name as string | undefined) ?? "";
      const lastName = (user.user_metadata?.last_name as string | undefined) ?? "";
      const displayName = `${firstName} ${lastName}`.trim() || user.email || "Me";

      const nodeW = 160;
      const nodeH = 60;

      const root = new shapes.standard.Rectangle({
        position: { x: Math.round(w / 2 - nodeW / 2), y: Math.round(h / 2 - nodeH / 2) },
        size: { width: nodeW, height: nodeH },
        attrs: {
          root: { cursor: "pointer" },
          body: { fill: "#86efac", stroke: "#15803d", strokeWidth: 2, rx: 12, ry: 12 },
          label: {
            text: displayName,
            fill: "#166534",
            fontSize: 16,
            fontWeight: "700",
          },
        },
      });

      graph.addCell(root);

      cleanup = () => {
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        svgEl.removeEventListener("contextmenu", onContextMenu);
        svgEl.removeEventListener("wheel", onWheel);
        if (zoomRafRef.current !== null) { cancelAnimationFrame(zoomRafRef.current); zoomRafRef.current = null; }
        paper.remove();
        paperRef.current = null;
      };
    })();

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [user, animateToScale]);

  useEffect(() => {
    if (!helpOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setHelpOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [helpOpen]);

  if (loading || !user) return null;

  return (
    <div className="flex h-screen flex-col bg-background-light">
      <Navbar user={user} onLogin={() => {}} onSignup={() => {}} onSignOut={async () => { await signOut(); router.replace("/"); }} />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-0.5 border-b border-primary-200 bg-primary-50 px-6 py-3">
          <span className="text-sm font-semibold text-primary-900">Career Graph</span>
          <span className="text-xs text-neutral-500">—drag nodes to explore your path</span>
          <button
            onClick={() => setHelpOpen(true)}
            className="ml-auto inline-flex items-center gap-2 rounded-lg border border-primary-200 bg-white px-3 py-1.5 text-xs font-semibold text-primary-700 shadow-sm transition hover:bg-primary-100"
            aria-haspopup="dialog"
            aria-expanded={helpOpen}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full border border-primary-400 text-[11px]">?</span>
            How to use
          </button>
        </div>
        {/* Canvas */}
        <div className="relative flex-1 overflow-hidden">
          <div
            ref={containerRef}
            className="h-full w-full"
            role="img"
            aria-label="Interactive career graph. Drag to pan and use the zoom controls to explore your path."
          />

          {/* Zoom controls */}
          <div className="absolute bottom-6 right-6 flex flex-col gap-1 rounded-xl border border-primary-200 bg-white shadow-md overflow-hidden">
            <button
              onClick={() => zoom(1.2)}
              className="cursor-pointer flex h-9 w-9 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Zoom in"
            >
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="8" y1="2" x2="8" y2="14"/><line x1="2" y1="8" x2="14" y2="8"/></svg>
            </button>
            <div className="h-px bg-primary-200" />
            <button
              onClick={() => zoom(1 / 1.2)}
              className="cursor-pointer flex h-9 w-9 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Zoom out"
            >
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="2" y1="8" x2="14" y2="8"/></svg>
            </button>
            <div className="h-px bg-primary-200" />
            <button
              onClick={resetView}
              className="cursor-pointer flex h-9 w-9 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Reset view"
              title="Reset view"
            >
              <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 4V1h3"/><path d="M14 11v3h-3"/><path d="M1 4a7 7 0 0 1 12 2"/><path d="M14 11a7 7 0 0 1-12-2"/></svg>
            </button>
          </div>
        </div>
      </div>

      {helpOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-primary-950/25 px-4 backdrop-blur-sm"
          onClick={() => setHelpOpen(false)}
          role="presentation"
        >
          <section
            className="w-full max-w-2xl rounded-2xl border border-primary-100 bg-white p-6 shadow-2xl sm:p-8"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="graph-help-title"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Quick guide</p>
                <h2 id="graph-help-title" className="mt-2 text-2xl font-bold tracking-tight text-primary-950">Explore your career graph</h2>
                <p className="mt-2 text-sm leading-6 text-neutral-500">Move around the canvas, adjust your view, and use the graph as a starting point for your next career direction.</p>
              </div>
              <button
                onClick={() => setHelpOpen(false)}
                className="rounded-full p-2 text-neutral-500 transition hover:bg-primary-50 hover:text-primary-800"
                aria-label="Close how to use guide"
              >
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="3" x2="15" y2="15"/><line x1="15" y1="3" x2="3" y2="15"/></svg>
              </button>
            </div>

            <div className="mt-7 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700 shadow-sm">✦</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">1. Start at your node</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Your name marks the starting point of your career map.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700 shadow-sm">↔</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">2. Move around</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Drag empty canvas space to pan across the graph.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700">⌕</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">3. Find your view</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Scroll to zoom, or use the controls in the lower-right corner.</p>
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-primary-200 bg-white p-5">
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-primary-100 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-primary-700">Coming next</span>
                <h3 className="text-base font-semibold text-primary-950">How the AI guide will fit in</h3>
              </div>
              <div className="mt-4 grid gap-5 text-sm leading-6 text-neutral-600 sm:grid-cols-2">
                <div>
                  <p className="font-semibold text-primary-900">Ask about a direction</p>
                  <p className="mt-1">The chatbot will help turn your interests, skills, and goals into possible career paths. You might ask, “What roles combine design and research?” or “What should I learn next for data engineering?”</p>
                </div>
                <div>
                  <p className="font-semibold text-primary-900">Explore real opportunities</p>
                  <p className="mt-1">Relevant job postings will appear alongside suggested paths, with details such as the role, company, location, key skills, experience level, and a link to the original listing.</p>
                </div>
              </div>
              <p className="mt-4 border-t border-primary-100 pt-4 text-xs leading-5 text-neutral-500">This chatbot and job-posting experience is planned and is not available in the current graph yet. Recommendations will be starting points for exploration, not guarantees of employment.</p>
            </div>

            <div className="mt-6 flex flex-col gap-3 rounded-xl border border-primary-100 px-4 py-3 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
              <span><strong className="font-semibold text-primary-900">Tip:</strong> Use Reset view whenever you want to return to the center.</span>
              <button onClick={() => setHelpOpen(false)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-700">Got it</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <AuthProvider>
      <GraphContent />
    </AuthProvider>
  );
}
