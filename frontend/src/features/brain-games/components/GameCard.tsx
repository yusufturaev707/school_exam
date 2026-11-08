import { Link } from 'react-router';
import type { Game, GameDifficulty } from '../types';
import { CATEGORY_META, DIFFICULTY_META, GAME_ICON } from '../utils/meta';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

/** Dizayn: daraja nuqtalari (bd-dots). */
export function DifficultyDots({ difficulty, className }: { difficulty: GameDifficulty; className?: string }) {
  const { label, dots } = DIFFICULTY_META[difficulty];
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span className="bd-dots" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <i key={i} className={i <= dots ? 'on' : undefined} />
        ))}
      </span>
      {label}
    </span>
  );
}

/** Daraja oraligʻi, masalan “Oson–Qiyin”. */
export const levels = (g: Game) => (g.difficulties.length > 1 ? `${DIFFICULTY_META[g.difficulties[0]!].label}–${DIFFICULTY_META[g.difficulties.at(-1)!].label}` : DIFFICULTY_META[g.difficulties[0]!].label);

/**
 * Dizayn: GameCard (bd-game) — 56px rangli illyustratsiya plitasi, overline yoʻnalish, nom, “~3 daq · Oson–Qiyin”,
 * oʻngda ⭐ eng yaxshi ball yoki “Yangi”. `compact` — “Tez orada” kichik xira kartasi.
 */
export function GameCard({ game, compact = false, bestScore }: { game: Game; compact?: boolean; bestScore?: number | null }) {
  const meta = CATEGORY_META[game.category];

  if (compact || !game.isActive) {
    return (
      <div className={cn('bd-card bd-card--flat bd-game is-soon gap-2! bg-transparent! px-2.5! py-2!', meta.tone)} aria-label={`${game.title} — tez orada`}>
        <span className="bd-tile">
          <Icon name={GAME_ICON[game.kind]} size={18} />
        </span>
        <span className="t-xs text-ink-2">{game.title}</span>
      </div>
    );
  }

  return (
    <Link to={`/activities/play/${game.slug}`} className={cn('bd-card bd-game bd-tap tap-card px-3! py-2.5! text-inherit no-underline', meta.tone)}>
      <span className="bd-game__art size-14!">
        <Icon name={GAME_ICON[game.kind]} size={28} />
      </span>
      <div className="grow">
        <div className="t-over text-[var(--ci)]">{meta.short}</div>
        <div className="t-h3">{game.title}</div>
        <div className="t-xs faint">
          ~{game.durationMinutes} daq · {levels(game)}
        </div>
      </div>
      {game.completedCount === 0 ? (
        <span className="bd-chip bd-chip--soft is-brand">Yangi</span>
      ) : bestScore != null ? (
        <span className="bd-chip bd-chip--stat is-star" aria-label={`Eng yaxshi natija: ${bestScore} ball`}>
          <span className="bd-wiggle">
            <Icon name="star" size={16} />
          </span>
          <span aria-hidden="true">{bestScore}</span>
        </span>
      ) : (
        <Icon name="chevR" size={18} className="text-ink-3" />
      )}
    </Link>
  );
}
