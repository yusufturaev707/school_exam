import type { ExamResult } from '../types';
import { CircularProgress } from '@/components/ui/CircularProgress';

/** Raqam halqa ichiga sigʻishi uchun xonalar soniga qarab kichrayadi. */
function scoreFontSize(score: number): number {
  const digits = String(score).length;
  if (digits <= 2) return 76;
  return digits === 3 ? 60 : 46;
}

/** Natija bali — ekranda birinchi koʻzga tashlanadigan element. Faqat `bd-hero` foni ustida ishlatiladi. */
export function ResultScore({ totals, examTitle }: { totals: ExamResult['totals']; examTitle: string }) {
  const pct = Math.round(totals.percent);
  return (
    <div className="flex flex-col items-center text-center">
      <CircularProgress
        value={totals.score}
        max={totals.maxScore}
        size={200}
        stroke={14}
        color="var(--sun)"
        trackColor="rgba(255, 255, 255, .2)"
        label={`${totals.maxScore} balldan ${totals.score} ball, ${pct} foiz`}
      >
        <span className="tabular leading-none font-black tracking-[-.03em]" style={{ fontSize: scoreFontSize(totals.score) }}>
          {totals.score}
        </span>
        <span className="tabular mt-1.5 text-[17px] leading-tight font-extrabold">/ {totals.maxScore} ball</span>
      </CircularProgress>
      <span className="tabular mt-3 rounded-full bg-sun px-4 py-1 text-[18px] leading-6 font-black text-on-sun" aria-hidden="true">
        {pct}%
      </span>
      <p className="t-sm mt-2 opacity-90">{examTitle}</p>
    </div>
  );
}
