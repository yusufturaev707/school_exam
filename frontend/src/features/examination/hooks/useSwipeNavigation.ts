import { useRef, type TouchEvent } from 'react';

interface Options {
  onNext: () => void;
  onPrev: () => void;
  enabled?: boolean;
  /** Minimum horizontal travel in px. */
  threshold?: number;
}

/**
 * Horizontal swipe between questions on touch screens.
 * Deliberately conservative so it never fights vertical scrolling or a tap on an answer:
 * the gesture must be clearly horizontal, quick, and must not start inside something that
 * scrolls sideways itself (wide formulas, the subject chips, inputs).
 */
export function useSwipeNavigation({ onNext, onPrev, enabled = true, threshold = 70 }: Options) {
  const start = useRef<{ x: number; y: number; t: number } | null>(null);

  const onTouchStart = (e: TouchEvent) => {
    if (!enabled || e.touches.length !== 1) return;
    const target = e.target as HTMLElement;
    if (target.closest('.katex-display, input, textarea, [data-no-swipe]')) {
      start.current = null;
      return;
    }
    const t = e.touches[0]!;
    start.current = { x: t.clientX, y: t.clientY, t: Date.now() };
  };

  const onTouchEnd = (e: TouchEvent) => {
    const s = start.current;
    start.current = null;
    if (!enabled || !s) return;
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - s.x;
    const dy = t.clientY - s.y;
    const dt = Date.now() - s.t;
    if (Math.abs(dx) < threshold || Math.abs(dx) < Math.abs(dy) * 1.8 || dt > 700) return;
    if (dx < 0) onNext();
    else onPrev();
  };

  return { onTouchStart, onTouchEnd, onTouchCancel: () => (start.current = null) };
}
