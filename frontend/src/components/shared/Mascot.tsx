import { cn } from '@/lib/cn';

/*
 * Bilimdon maskoti — yashil kitob, katta koʻzli, sariq xatchoʻpli.
 * bilimdon-dizayn/dizayn-tizimi/components/bundle.js dagi `Bilimdon.mascot(mood)` ning React varianti.
 * Kayfiyatlar: salom, ishora, oylayapti, xursand, hayron. Ranglar ikkala rejimda oʻzgarmaydi.
 * Bir ekranda bitta maskot.
 */
export type MascotMood = 'salom' | 'ishora' | 'oylayapti' | 'xursand' | 'hayron' | /* eski nomlar */ 'wave' | 'happy' | 'think' | 'calm';

const LEGACY: Record<string, MascotMood> = { wave: 'salom', happy: 'xursand', think: 'oylayapti', calm: 'salom' };

const M = { body: '#2e8b74', spine: '#1f6f5f', page: '#fff6df', mark: '#ffc94a', ink: '#11302a', cheek: '#ff9fae' };

function Eye({ cx, cy, dx, dy }: { cx: number; cy: number; dx: number; dy: number }) {
  return (
    <>
      <circle cx={cx} cy={cy} r="11" fill="#fff" />
      <circle cx={cx + dx} cy={cy + dy} r="5.6" fill={M.ink} />
      <circle cx={cx + dx + 2} cy={cy + dy - 2.2} r="1.9" fill="#fff" />
    </>
  );
}

function Arm({ d }: { d: string }) {
  return (
    <>
      <path d={d} stroke={M.ink} strokeWidth="8.5" strokeLinecap="round" fill="none" />
      <path d={d} stroke={M.body} strokeWidth="5" strokeLinecap="round" fill="none" />
    </>
  );
}

function Hand({ x, y }: { x: number; y: number }) {
  return <circle cx={x} cy={y} r="5" fill={M.body} stroke={M.ink} strokeWidth="2" />;
}

export interface MascotProps {
  mood?: MascotMood;
  /** Balandlik px da (kenglik 120/140 nisbatda). `className` bilan oʻlcham berilsa shart emas. */
  size?: number;
  className?: string;
  /** Berilsa — maʼnoli rasm; aks holda bezak (screen reader eʼtibor bermaydi). */
  title?: string;
}

export function Mascot({ mood: rawMood = 'salom', size, className, title }: MascotProps) {
  const mood = LEGACY[rawMood] ?? rawMood;
  let eyes, mouth, arms, extra, brows;

  if (mood === 'xursand') {
    eyes = <path d="M41 54q9-11 18 0M65 54q9-11 18 0" stroke={M.ink} strokeWidth="4.5" strokeLinecap="round" fill="none" />;
    mouth = (
      <>
        <path d="M50 70q12 14 24 0z" fill={M.ink} />
        <path d="M55 75q7 4 14 0" stroke="#ff8a9b" strokeWidth="3" strokeLinecap="round" fill="none" />
      </>
    );
    arms = (
      <g className="bd-m-cheer">
        <Arm d="M24 70Q12 56 10 40" />
        <Hand x={10} y={38} />
        <Arm d="M96 70Q108 56 110 40" />
        <Hand x={110} y={38} />
      </g>
    );
    extra = (
      <>
        <path d="M14 18l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill={M.mark} />
        <path d="M104 10l1.6 4 4 1.6-4 1.6-1.6 4-1.6-4-4-1.6 4-1.6z" fill={M.mark} />
      </>
    );
  } else if (mood === 'oylayapti') {
    eyes = (
      <>
        <Eye cx={50} cy={52} dx={2.5} dy={-4} />
        <Eye cx={74} cy={52} dx={2.5} dy={-4} />
      </>
    );
    mouth = <path d="M56 74q6-3 12 0" stroke={M.ink} strokeWidth="3.5" strokeLinecap="round" fill="none" />;
    arms = (
      <>
        <Arm d="M24 76Q12 86 18 100" />
        <Hand x={18} y={101} />
        <Arm d="M96 78Q86 84 76 78" />
        <Hand x={74} y={77} />
      </>
    );
    extra = (
      <g transform="translate(92 -2)">
        <circle cx="12" cy="12" r="9" fill={M.mark} />
        <rect x="8" y="20" width="8" height="5" rx="2" fill={M.spine} />
        <path d="M12 -2v-3M24 8l3-2M0 8l-3-2" stroke={M.mark} strokeWidth="2.5" strokeLinecap="round" />
      </g>
    );
  } else if (mood === 'ishora') {
    eyes = (
      <>
        <Eye cx={50} cy={52} dx={-4} dy={1} />
        <Eye cx={74} cy={52} dx={-4} dy={1} />
      </>
    );
    mouth = <path d="M52 70q10 9 20 0" stroke={M.ink} strokeWidth="3.5" strokeLinecap="round" fill="none" />;
    arms = (
      <>
        <g className="bd-m-point">
          <Arm d="M26 74Q16 72 8 76" />
          <Hand x={7} y={76} />
        </g>
        <Arm d="M96 76Q106 88 102 100" />
        <Hand x={102} y={101} />
      </>
    );
  } else if (mood === 'hayron') {
    eyes = (
      <>
        <Eye cx={50} cy={54} dx={0} dy={1} />
        <Eye cx={74} cy={54} dx={0} dy={1} />
      </>
    );
    brows = <path d="M41 42l14-5M83 42l-14-5" stroke={M.ink} strokeWidth="3.5" strokeLinecap="round" />;
    mouth = <path d="M54 76q3-4 6 0t6 0t6 0" stroke={M.ink} strokeWidth="3.5" strokeLinecap="round" fill="none" />;
    arms = (
      <>
        <Arm d="M24 76Q14 88 18 100" />
        <Hand x={18} y={101} />
        <Arm d="M96 76Q106 88 102 100" />
        <Hand x={102} y={101} />
      </>
    );
  } else {
    /* salom */
    eyes = (
      <>
        <Eye cx={50} cy={52} dx={1} dy={1} />
        <Eye cx={74} cy={52} dx={1} dy={1} />
      </>
    );
    mouth = <path d="M50 69q12 12 24 0" stroke={M.ink} strokeWidth="3.5" strokeLinecap="round" fill="none" />;
    arms = (
      <>
        <Arm d="M24 76Q14 88 18 100" />
        <Hand x={18} y={101} />
        <g className="bd-m-wave">
          <Arm d="M96 72Q110 60 108 42" />
          <Hand x={108} y={40} />
        </g>
      </>
    );
  }

  const h = size;
  const w = size ? Math.round((size * 120) / 140) : undefined;

  return (
    <svg
      className={cn('bd-mascot shrink-0', className)}
      width={w}
      height={h}
      viewBox="0 0 120 140"
      fill="none"
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <rect x="40" y="116" width="12" height="18" rx="6" fill={M.ink} />
      <rect x="68" y="116" width="12" height="18" rx="6" fill={M.ink} />
      <rect x="31" y="20" width="68" height="102" rx="14" fill={M.page} />
      <path d="M93 30v82" stroke="#ead9b4" strokeWidth="2" />
      <rect x="24" y="16" width="70" height="104" rx="14" fill={M.body} />
      <path d="M38 16h-0a14 14 0 0 0-14 14v76a14 14 0 0 0 14 14z" fill={M.spine} />
      <path d="M74 8h12v28l-6-5-6 5z" fill={M.mark} />
      {arms}
      {brows}
      {eyes}
      <circle cx="40" cy="66" r="4.5" fill={M.cheek} opacity=".55" />
      <circle cx="84" cy="66" r="4.5" fill={M.cheek} opacity=".55" />
      {mouth}
      {extra}
    </svg>
  );
}
