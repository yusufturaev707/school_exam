import { useState } from 'react';
import type { Game, GameDifficulty } from '../types';
import { CATEGORY_META, DIFFICULTY_META } from '../utils/meta';
import { GameIllustration } from './GameIllustration';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { Mascot } from '@/components/shared/Mascot';
import { Steps, Sticky, TopBar } from '@/components/shared/design';
import { cn } from '@/lib/cn';

interface Props {
  game: Game;
  /** Set when this visit is today's daily challenge: the level is fixed for the reward. */
  daily: { difficulty: GameDifficulty; bonus: number } | null;
  /** Last level the student picked for this game (kept across reloads). */
  initialDifficulty?: GameDifficulty;
  starting: boolean;
  error: string | null;
  onStart: (difficulty: GameDifficulty) => void;
}

/** Dizayn: ScreenGames → “Oʻyin kirish ekrani”: illyustratsiya, 3 qadam, daraja segmenti, pastda yopishgan tugma. */
export function GameInstructions({ game, daily, initialDifficulty, starting, error, onStart }: Props) {
  const meta = CATEGORY_META[game.category];
  const [difficulty, setDifficulty] = useState<GameDifficulty>(
    daily?.difficulty ?? (initialDifficulty && game.difficulties.includes(initialDifficulty) ? initialDifficulty : game.difficulties[0]!),
  );

  return (
    <div className="mx-auto w-full max-w-[640px] px-4 pt-[env(safe-area-inset-top)] pb-40">
      <TopBar title="Laboratoriya" back="/activities" />

      <div className={cn('relative flex h-[132px] items-center justify-center rounded-[var(--radius-xl)]', meta.bg)}>
        <GameIllustration kind={game.kind} ink={meta.hex.ink} bg={meta.hex.bg} className="h-full" />
        <span className="absolute right-2 -bottom-1.5">
          <Mascot mood="oylayapti" size={64} />
        </span>
      </div>

      <p className={cn('t-over mt-4', meta.ink)}>
        {meta.short} · {game.title}
      </p>
      <h1 className="t-hero mt-0.5">{game.intro.title}</h1>
      <p className="t-sm muted mt-1">{game.intro.text}</p>

      {daily && (
        <p className="t-sm mt-3 flex items-start gap-2 rounded-[var(--radius-md)] bg-star-soft p-3 text-star-ink">
          <Icon name="sun" size={18} />
          Bu — bugungi topshiriq. Uni yakunlasang, {daily.bonus > 0 ? `+${daily.bonus} ⭐ bonus va ` : ''}kunlik yutuqqa ega boʻlasan!
        </p>
      )}

      {game.instructions.length > 0 && (
        <div className="mt-3.5">
          <Steps compact tone={meta.tone} items={game.instructions.map((text) => ({ text }))} />
        </div>
      )}

      {!daily && game.difficulties.length > 1 && (
        <>
          <p className="t-h3 mt-6 mb-2" id="level-label">
            Darajani tanla
          </p>
          <div className="bd-seg" role="radiogroup" aria-labelledby="level-label">
            {game.difficulties.map((d) => (
              <button key={d} type="button" role="radio" aria-checked={difficulty === d} className={cn(difficulty === d && 'is-on')} onClick={() => setDifficulty(d)}>
                <span className="bd-dots" aria-hidden="true">
                  {[1, 2, 3].map((i) => (
                    <i key={i} className={i <= DIFFICULTY_META[d].dots ? 'on' : undefined} />
                  ))}
                </span>
                {DIFFICULTY_META[d].label}
              </button>
            ))}
          </div>
        </>
      )}

      <Sticky note={`Taxminan ${game.durationMinutes} daqiqa · shoshilish shart emas`}>
        {error && (
          <p role="alert" className="t-sm flex items-start gap-2 text-danger-ink">
            <Icon name="alert" size={18} />
            {error}
          </p>
        )}
        <Button fullWidth loading={starting} onClick={() => onStart(difficulty)} rightIcon={<Icon name="play" />} aria-label={`Oʻyinni boshlash, ${DIFFICULTY_META[difficulty].label} daraja`}>
          Oʻyinni boshlash
        </Button>
      </Sticky>
    </div>
  );
}
