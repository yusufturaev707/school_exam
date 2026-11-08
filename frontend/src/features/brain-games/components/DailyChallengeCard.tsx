import { Link } from 'react-router';
import type { DailyChallenge } from '../types';
import { CATEGORY_META, DIFFICULTY_META, GAME_ICON } from '../utils/meta';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';

/** Dizayn: “Bugungi topshiriq” hero (ScreenGames) — bir kunda bitta, bir marta mukofotlanadi. */
export function DailyChallengeCard({ daily }: { daily: DailyChallenge }) {
  const meta = CATEGORY_META[daily.game.category];
  return (
    <section aria-labelledby="daily-title" className="bd-hero px-4! py-3.5!">
      <div className="row">
        <span className="bd-chip bd-chip--status">
          <Icon name="sun" size={14} />
          Bugungi topshiriq
        </span>
      </div>
      <div className="row mt-2.5 gap-3!">
        <span className="bd-game__art bg-white/14! text-sun!">
          <Icon name={GAME_ICON[daily.game.kind]} size={30} />
        </span>
        <div className="grow">
          <h2 id="daily-title" className="t-h2">
            {daily.game.title}
          </h2>
          <div className="t-sm opacity-85">
            {meta.short} · {DIFFICULTY_META[daily.difficulty].label} · ~{daily.game.durationMinutes} daqiqa
          </div>
        </div>
        {!daily.completed && daily.bonus > 0 && <span className="bd-chip bd-chip--glass">+{daily.bonus} ⭐</span>}
      </div>

      {daily.completed ? (
        <p className="mt-3.5 flex items-center gap-2 rounded-[var(--radius-md)] bg-white/14 px-4 py-3 text-[15px] font-bold">
          <Icon name="check" className="text-sun" />
          Barakalla! Bugungi topshiriq bajarildi. Ertaga yangisi boʻladi.
        </p>
      ) : (
        <Link to={`/activities/play/${daily.game.slug}?daily=1`} className={buttonClass('light', { fullWidth: true, className: 'mt-3.5' })}>
          Topshiriqni boshlash
          <Icon name="play" />
        </Link>
      )}
    </section>
  );
}
