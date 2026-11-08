import { Link } from 'react-router';
import type { Dashboard } from '../types';
import type { GameStatistics } from '@/features/brain-games/types';
import { CATEGORY_META } from '@/features/brain-games/utils/meta';
import { Icon, type IconName } from '@/components/ui/Icon';
import { formatDay } from '@/lib/date';
import { cn } from '@/lib/cn';

interface Row {
  key: string;
  to: string;
  tone: string;
  icon: IconName;
  title: string;
  sub: string;
  value: string;
  at: string;
}

/** Dizayn: “Soʻnggi faoliyat” — imtihon va oʻyinlar bitta roʻyxatda, eng yangisi tepada. */
export function buildActivity(exams: Dashboard['recentActivity'], games: GameStatistics['recent'] = []): Row[] {
  const rows: Row[] = [
    ...exams.map((e) => ({
      key: `e-${e.resultId}`,
      to: `/results/${e.resultId}`,
      tone: 'is-brand',
      icon: 'exam' as IconName,
      title: e.examTitle,
      sub: `${formatDay(e.completedAt)} · ${e.status === 'completed' ? 'Yakunlangan' : 'Vaqt tugagan'}`,
      value: `${e.correct}/${e.total}`,
      at: e.completedAt,
    })),
    ...games.map((g) => ({
      key: `g-${g.sessionId}`,
      to: `/activities/result/${g.sessionId}`,
      tone: CATEGORY_META[g.category].tone,
      icon: CATEGORY_META[g.category].icon,
      title: g.title,
      sub: `${formatDay(g.completedAt)} · ${CATEGORY_META[g.category].short}`,
      value: `+${g.score + g.bonus} ⭐`,
      at: g.completedAt,
    })),
  ];
  return rows.sort((a, b) => b.at.localeCompare(a.at));
}

export function RecentActivity({ rows, limit = 3 }: { rows: Row[]; limit?: number }) {
  if (rows.length === 0) return <p className="bd-card t-sm muted">Hozircha faoliyat yoʻq.</p>;
  return (
    <ul className="bd-card bd-list px-4! py-0.5!">
      {rows.slice(0, limit).map((r) => (
        <li key={r.key} className="p-0!">
          <Link to={r.to} aria-label={`${r.title}, ${r.sub}, ${r.value.replace('⭐', 'ball')}`} className={cn('bd-rowcard tap-card min-h-[52px] py-2.5 text-inherit no-underline', r.tone)}>
            <span className="bd-tile">
              <Icon name={r.icon} />
            </span>
            <div className="grow">
              <div className="t-h3 truncate">{r.title}</div>
              <div className="t-xs faint">{r.sub}</div>
            </div>
            <b className="t-h3 tabular">{r.value}</b>
          </Link>
        </li>
      ))}
    </ul>
  );
}
