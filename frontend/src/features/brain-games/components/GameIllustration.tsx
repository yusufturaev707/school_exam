import type { GameKind } from '../types';
import { cn } from '@/lib/cn';

/**
 * Small inline-SVG scene per game: recognisable at a glance, no image requests, crisp on any screen.
 * Decorative — the card title carries the meaning for screen readers.
 */
export function GameIllustration({ kind, className, ink, bg }: { kind: GameKind; className?: string; ink: string; bg: string }) {
  return (
    // Ranglar CSS oʻzgaruvchilari (var(--logic-ink)…) — SVG atributlari var() ni qabul qilmaydi, shuning uchun currentColor/style orqali.
    <svg viewBox="0 0 160 100" className={cn('block', className)} style={{ color: ink }} aria-hidden="true">
      <rect width="160" height="100" rx="18" style={{ fill: bg }} />
      <circle cx="140" cy="14" r="22" fill="#fff" opacity="0.3" />
      <circle cx="16" cy="92" r="16" fill="#fff" opacity="0.25" />
      <Scene kind={kind} ink="currentColor" />
    </svg>
  );
}

function Scene({ kind, ink }: { kind: GameKind; ink: string }) {
  switch (kind) {
    case 'memory':
      return (
        <g>
          <g transform="rotate(-8 56 52)">
            <rect x="34" y="22" width="44" height="58" rx="10" fill={ink} />
            <text x="56" y="60" textAnchor="middle" fontSize="28" fontWeight="900" fill="#fff" opacity="0.9">?</text>
          </g>
          <g transform="rotate(7 104 50)">
            <rect x="82" y="20" width="44" height="58" rx="10" fill="#fff" stroke={ink} strokeWidth="3" />
            <circle cx="104" cy="52" r="12" fill="#E8574F" />
            <path d="M104 40c2-5 6-7 10-6-2 4-6 6-10 6z" fill="#35A875" />
          </g>
        </g>
      );
    case 'missing-number':
      return (
        <g fontWeight="900" fontSize="20" textAnchor="middle">
          {['2', '4', '?', '8'].map((t, i) => (
            <g key={i} transform={`translate(${22 + i * 31} 32)`}>
              <rect width="26" height="34" rx="8" fill={t === '?' ? ink : '#fff'} stroke={ink} strokeWidth="2.5" strokeDasharray={t === '?' ? '0' : '0'} />
              <text x="13" y="24" fill={t === '?' ? '#fff' : ink}>{t}</text>
            </g>
          ))}
        </g>
      );
    case 'pattern':
      return (
        <g>
          <circle cx="32" cy="50" r="13" fill="#F2B84B" />
          <rect x="52" y="37" width="26" height="26" rx="5" fill={ink} />
          <circle cx="98" cy="50" r="13" fill="#F2B84B" />
          <rect x="116" y="35" width="30" height="30" rx="8" fill="#fff" stroke={ink} strokeWidth="2.5" strokeDasharray="5 4" />
          <text x="131" y="57" textAnchor="middle" fontSize="18" fontWeight="900" fill={ink}>?</text>
        </g>
      );
    case 'odd-one-out':
      return (
        <g>
          <circle cx="36" cy="50" r="13" fill={ink} opacity="0.85" />
          <circle cx="66" cy="50" r="13" fill={ink} opacity="0.85" />
          <circle cx="96" cy="50" r="13" fill={ink} opacity="0.85" />
          <path d="M126 36l15 27h-30z" fill="#F2B84B" />
          <circle cx="126" cy="54" r="22" fill="none" stroke="#E8574F" strokeWidth="3" strokeDasharray="4 4" />
        </g>
      );
    case 'quick-math':
      return (
        <g>
          <rect x="30" y="26" width="100" height="48" rx="14" fill="#fff" stroke={ink} strokeWidth="3" />
          <text x="80" y="58" textAnchor="middle" fontSize="22" fontWeight="900" fill={ink}>7 × 8</text>
          <path d="M126 22l6-10M134 30l10-4" stroke="#F2B84B" strokeWidth="4" strokeLinecap="round" />
        </g>
      );
    case 'maze':
      return (
        <g fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round">
          <path d="M40 22h80v56H40zM40 40h28M92 22v24M68 58h32M120 58h-12M68 40v18" />
          <circle cx="50" cy="69" r="6" fill="#F2B84B" stroke="none" />
          <path d="M130 30l6 0" stroke="#35A875" />
        </g>
      );
    case 'word-search':
      return (
        <g fontWeight="900" fontSize="14" textAnchor="middle" fill={ink}>
          {['K', 'I', 'T', 'O', 'B', 'A', 'L', 'M', 'O'].map((ch, i) => (
            <text key={i} x={56 + (i % 3) * 24} y={36 + Math.floor(i / 3) * 22}>{ch}</text>
          ))}
          <rect x="44" y="22" width="72" height="20" rx="10" fill="none" stroke="#F2B84B" strokeWidth="3" />
        </g>
      );
  }
}
