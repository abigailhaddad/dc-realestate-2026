"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, LayoutDashboard, Maximize, Minimize } from "lucide-react";

export function Slide({ children }: { children: ReactNode }) {
  return (
    <section className="flex min-h-screen w-full flex-col overflow-y-auto px-6 sm:px-16 md:px-24">
      {/* my-auto centers the slide vertically when content fits the viewport;
          when content is taller than the screen, my-auto collapses to 0 and
          we get normal scroll behavior. */}
      <div className="mx-auto my-auto w-full max-w-5xl py-12">{children}</div>
    </section>
  );
}

export function SlideTitle({ children, eyebrow }: { children: ReactNode; eyebrow?: string }) {
  return (
    <header className="mb-8">
      {eyebrow && (
        <div className="mb-4 text-sm font-medium uppercase tracking-[0.18em]"
             style={{ color: "#2D6A4F" /* Forest Green eyebrow */ }}>
          {eyebrow}
        </div>
      )}
      <h2 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl md:text-6xl">
        {children}
      </h2>
    </header>
  );
}

export function SlideBody({ children }: { children: ReactNode }) {
  return <div className="text-xl leading-relaxed text-foreground/90">{children}</div>;
}

export function Deck({ slides }: { slides: ReactNode[] }) {
  const [idx, setIdx] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    function onFsChange() {
      setIsFullscreen(!!document.fullscreenElement);
    }
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  const go = useCallback(
    (delta: number) => {
      setIdx((i) => Math.max(0, Math.min(slides.length - 1, i + delta)));
    },
    [slides.length],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        go(-1);
      } else if (e.key === "Home") {
        setIdx(0);
      } else if (e.key === "End") {
        setIdx(slides.length - 1);
      } else if (e.key === "f" || e.key === "F") {
        toggleFullscreen();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, slides.length]);

  return (
    <div className="deck relative min-h-screen w-full bg-background">
      {slides[idx]}

      <div className="pointer-events-none fixed inset-x-0 bottom-0 flex items-center justify-between px-4 pb-4 z-50">
        <div className="pointer-events-auto flex items-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-md border border-input bg-background/80 px-3 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur hover:bg-accent hover:text-accent-foreground"
          >
            <LayoutDashboard className="size-3.5" /> Dashboard
          </Link>
          <button
            onClick={toggleFullscreen}
            className="inline-flex items-center gap-2 rounded-md border border-input bg-background/80 px-3 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur hover:bg-accent hover:text-accent-foreground"
            title={isFullscreen ? "Exit fullscreen (F)" : "Present fullscreen (F)"}
          >
            {isFullscreen ? <Minimize className="size-3.5" /> : <Maximize className="size-3.5" />}
            {isFullscreen ? "Exit" : "Present"}
          </button>
        </div>

        <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-input bg-background/90 px-3 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur shadow-sm">
          <button
            onClick={() => go(-1)}
            disabled={idx === 0}
            aria-label="Previous slide"
            className="inline-flex size-6 items-center justify-center rounded hover:bg-accent disabled:opacity-30"
          >
            <ArrowLeft className="size-3.5" />
          </button>
          <span className="tabular-nums">
            {idx + 1} / {slides.length}
          </span>
          <button
            onClick={() => go(1)}
            disabled={idx === slides.length - 1}
            aria-label="Next slide"
            className="inline-flex size-6 items-center justify-center rounded hover:bg-accent disabled:opacity-30"
          >
            <ArrowRight className="size-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
