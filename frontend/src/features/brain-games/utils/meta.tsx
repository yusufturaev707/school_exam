import type { GameCategory, GameDifficulty, GameKind } from '../types';
import { Icon, type IconName } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

export interface CategoryMeta {
  title: string;
  /** Qisqa nom (yoʻnalish gridi). */
  short: string;
  icon: IconName;
  /** Dizayn rang toʻplami: `is-memory`, `is-logic`, … */
  tone: string;
  /** Yumshoq fon. */
  bg: string;
  /** Matn/ikonka rangi — `bg` ustida AA. */
  ink: string;
  /** Toʻyingan rang (progress). */
  solid: string;
  /** SVG illyustratsiyalar uchun CSS oʻzgaruvchilari (yorugʻ/qorongʻi rejimga moslashadi). */
  hex: { bg: string; ink: string };
}

export const CATEGORY_META: Record<GameCategory, CategoryMeta> = {
  memory: { title: 'Xotira', short: 'Xotira', icon: 'brain', tone: 'is-memory', bg: 'bg-memory-soft', ink: 'text-memory-ink', solid: 'bg-memory-solid', hex: { bg: 'var(--memory-soft)', ink: 'var(--memory-ink)' } },
  logic: { title: 'Mantiq', short: 'Mantiq', icon: 'puzzle', tone: 'is-logic', bg: 'bg-logic-soft', ink: 'text-logic-ink', solid: 'bg-logic', hex: { bg: 'var(--logic-soft)', ink: 'var(--logic-ink)' } },
  math: { title: 'Matematika', short: 'Matematika', icon: 'sigma', tone: 'is-math', bg: 'bg-math-soft', ink: 'text-math-ink', solid: 'bg-math-solid', hex: { bg: 'var(--math-soft)', ink: 'var(--math-ink)' } },
  attention: { title: 'Diqqat', short: 'Diqqat', icon: 'eye', tone: 'is-attn', bg: 'bg-attn-soft', ink: 'text-attn-ink', solid: 'bg-attn', hex: { bg: 'var(--attn-soft)', ink: 'var(--attn-ink)' } },
  spatial: { title: 'Fazoviy fikrlash', short: 'Fazoviy', icon: 'compass', tone: 'is-spatial', bg: 'bg-spatial-soft', ink: 'text-spatial-ink', solid: 'bg-spatial-solid', hex: { bg: 'var(--spatial-soft)', ink: 'var(--spatial-ink)' } },
  language: { title: 'Soʻz va til', short: 'Soʻz va til', icon: 'text', tone: 'is-lang', bg: 'bg-lang-soft', ink: 'text-lang-ink', solid: 'bg-lang', hex: { bg: 'var(--lang-soft)', ink: 'var(--lang-ink)' } },
};

export const CATEGORY_ORDER: GameCategory[] = ['memory', 'logic', 'math', 'attention', 'spatial', 'language'];

/** Oʻyin kartasi illyustratsiyasi oʻrnidagi ikonka (dizayn: GameCard). */
export const GAME_ICON: Record<GameKind, IconName> = {
  memory: 'grid',
  'missing-number': 'sigma',
  pattern: 'puzzle',
  'odd-one-out': 'eye',
  'quick-math': 'calc',
  maze: 'compass',
  'word-search': 'text',
};

export const DIFFICULTY_META: Record<GameDifficulty, { label: string; dots: number }> = {
  easy: { label: 'Oson', dots: 1 },
  medium: { label: 'Oʻrtacha', dots: 2 },
  hard: { label: 'Qiyin', dots: 3 },
};

/** Dizayn: bd-tile — `sm` 28px, `md` 32px, `lg` 40px. */
export function CategoryIcon({ category, size = 'md', className }: { category: GameCategory; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const meta = CATEGORY_META[category];
  return (
    <span aria-hidden="true" className={cn('bd-tile', meta.tone, size === 'sm' && 'size-7!', size === 'lg' && 'bd-tile--lg', className)}>
      <Icon name={meta.icon} size={size === 'sm' ? 16 : size === 'lg' ? 22 : 20} />
    </span>
  );
}

/** Achievement icon ids come from the backend; unknown ids fall back to a trophy. */
const ACHIEVEMENT_ICONS: Record<string, IconName> = { footprints: 'flag', brain: 'brain', calculator: 'calc', puzzle: 'puzzle', eye: 'eye', compass: 'compass', sun: 'sun' };
export const achievementIcon = (id: string): IconName => ACHIEVEMENT_ICONS[id] ?? 'trophy';
/** Nishon rangi — ikonka boʻyicha (dizayn: Badge). */
const ACHIEVEMENT_TONES: Record<string, string> = { footprints: 'is-memory', brain: 'is-logic', calculator: 'is-math', puzzle: 'is-logic', eye: 'is-attn', compass: 'is-spatial', sun: 'is-star' };
export const achievementTone = (id: string): string => ACHIEVEMENT_TONES[id] ?? 'is-brand';

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s} soniya`;
  return s === 0 ? `${m} daqiqa` : `${m} daqiqa ${s} soniya`;
}

export const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
