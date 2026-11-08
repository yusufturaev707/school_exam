import { Link } from 'react-router';
import type { DailyChallenge } from '@/features/brain-games/types';
import { DIFFICULTY_META } from '@/features/brain-games/utils/meta';
import { Ring } from '@/components/ui/CircularProgress';
import { StatChip } from '@/components/shared/design';
import { Icon } from '@/components/ui/Icon';

/** Dizayn: MissionCard (bd-mission) — progress halqasi, “KUNLIK MISSIYA”, mukofot chipi. */
export function MissionCard({ daily }: { daily: DailyChallenge }) {
  const done = daily.completed;
  return (
    <Link
      to={done ? '/activities' : `/activities/play/${daily.game.slug}?daily=1`}
      className="bd-card bd-mission bd-tap tap-card text-inherit no-underline"
      aria-label={`Kunlik missiya: ${daily.game.title}${done ? ', bajarildi' : ''}`}
    >
      <Ring percent={done ? 100 : 0} className="is-brand">
        {done ? <Icon name="check" size={16} className="text-brand" /> : '0/1'}
      </Ring>
      <div className="grow">
        <div className="t-over text-brand-ink">Kunlik missiya</div>
        <div className="bd-mission__title">{done ? 'Barakalla! Missiya bajarildi' : 'Bugungi topshiriqni bajar'}</div>
        <div className="bd-mission__sub">
          Topshiriq: {daily.game.title} · {DIFFICULTY_META[daily.difficulty].label}
        </div>
      </div>
      {done || daily.bonus === 0 ? (
        <Icon name="chevR" size={18} className="text-ink-3" />
      ) : (
        <StatChip kind="star" label={`Mukofot: ${daily.bonus} bonus ball`}>
          +{daily.bonus}
        </StatChip>
      )}
    </Link>
  );
}
