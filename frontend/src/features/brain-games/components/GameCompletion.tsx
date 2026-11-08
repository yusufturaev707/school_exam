import { Link } from 'react-router';
import type { GameResult } from '../types';
import { completionMessage } from '../utils/feedback';
import { CATEGORY_META, DIFFICULTY_META, achievementIcon, achievementTone } from '../utils/meta';
import { Mascot } from '@/components/shared/Mascot';
import { Confetti } from '@/components/shared/Confetti';
import { StatTile, StatTiles, Sticky } from '@/components/shared/design';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

const shortDuration = (s: number) => (s < 60 ? `${s} s` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`);

/** Dizayn: ScreenPlay → “Oʻyin natijasi”: konfetti, xursand maskot, ball/urinish/vaqt, yangi nishon, “Yana oʻynash”. */
export function GameCompletion({ result }: { result: GameResult }) {
  const msg = completionMessage(result);
  const meta = CATEGORY_META[result.game.category];
  const isMemory = result.moves !== null;

  return (
    <div className="relative">
      <Confetti />
      <div className="flex flex-col items-center pt-7 text-center">
        <Mascot mood="xursand" size={128} />
        <p className={cn('t-over mt-3', meta.ink)}>
          {result.game.title} · {DIFFICULTY_META[result.difficulty].label}
        </p>
        <h1 className="t-hero mt-1">{msg.title}</h1>
        <p className="t-sm muted mt-1 max-w-[300px]">{msg.text}</p>
      </div>

      <StatTiles className="mt-4">
        <StatTile icon="star" value={result.score} label="ball" tone="is-star" center />
        {isMemory ? (
          <StatTile icon="target" value={result.moves} label="urinish" tone="is-memory" center />
        ) : (
          <StatTile icon="check" value={`${result.correctAnswers}/${result.totalQuestions}`} label="toʻgʻri" tone="is-memory" center />
        )}
        <StatTile icon="clock" value={shortDuration(result.durationSeconds)} label="vaqt" tone="is-attn" center />
      </StatTiles>

      {result.isDaily && (
        <div className="bd-card bd-rowcard is-star mt-3 bg-star-soft! shadow-none!">
          <span className="bd-tile bg-card!">
            <Icon name="sun" />
          </span>
          <div className="grow">
            <div className="t-over text-star-ink">Bugungi topshiriq</div>
            <div className="t-h3">Bajarildi!</div>
          </div>
          {result.bonus > 0 && <b className="t-h3 tabular text-star-ink">+{result.bonus} bonus ⭐</b>}
        </div>
      )}
      {result.bonus > 0 && (
        <p className="t-sm muted mt-2 text-center">
          Jami: <b className="tabular text-ink">{result.score + result.bonus} ⭐</b> ({result.score} ball + {result.bonus} bonus)
        </p>
      )}

      {result.newAchievements.map((a) => (
        <div key={a.id} className={cn('bd-card bd-rowcard mt-3 shadow-none!', achievementTone(a.icon))} style={{ background: 'var(--cs)' }}>
          <span className="bd-badge__disc size-11! shadow-[0_0_0_3px_var(--card)]!">
            <Icon name={achievementIcon(a.icon)} size={22} />
          </span>
          <div className="grow">
            <div className="t-over text-[var(--ci)]">Yangi nishon!</div>
            <div className="t-h3">{a.title}</div>
          </div>
          <span className="t-xs text-[var(--ci)]">+1 yutuq</span>
        </div>
      ))}

      <Sticky>
        <Link to={`/activities/play/${result.game.slug}`} className={buttonClass('primary', { fullWidth: true })}>
          <Icon name="retry" />
          Yana oʻynash
        </Link>
        <Link to="/activities" className={buttonClass('ghost', { fullWidth: true })}>
          Laboratoriyaga qaytish
        </Link>
      </Sticky>
    </div>
  );
}
