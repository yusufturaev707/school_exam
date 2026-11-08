import { Link } from 'react-router';
import { useResult, useResults } from '../api/resultsApi';
import type { ResultSummary } from '../types';
import { useDailyChallenge, useGameStatistics } from '@/features/brain-games/hooks/useGames';
import { CATEGORY_META, GAME_ICON } from '@/features/brain-games/utils/meta';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { Ring } from '@/components/ui/CircularProgress';
import { ErrorState } from '@/components/feedback/ErrorState';
import { Mascot } from '@/components/shared/Mascot';
import { PageTitle, Section } from '@/components/shared/design';
import { SUBJECTS, SUBJECT_ORDER, SubjectIcon } from '@/components/shared/subjects';
import { formatDay } from '@/lib/date';
import { cn } from '@/lib/cn';

/** Boʻsh holatda — mashq taklifi (bugungi topshiriq). */
function PracticeSuggestion() {
  const { data } = useDailyChallenge();
  if (!data) return null;
  const meta = CATEGORY_META[data.game.category];
  return (
    <Section title="Shu orada mashq qil" id="practice-title">
      <Link to={`/activities/play/${data.game.slug}${data.completed ? '' : '?daily=1'}`} className={cn('bd-card bd-game bd-tap tap-card px-3! py-2.5! text-inherit no-underline', meta.tone)}>
        <span className="bd-game__art size-12!">
          <Icon name={GAME_ICON[data.game.kind]} size={24} />
        </span>
        <div className="grow">
          <div className="t-h3">{data.game.title}</div>
          <div className="t-xs faint">{data.completed ? `${meta.short} · yana oʻynash` : data.bonus > 0 ? `Bugungi topshiriq · +${data.bonus} ⭐` : 'Bugungi topshiriq'}</div>
        </div>
        <Icon name="chevR" size={18} className="text-ink-3" />
      </Link>
    </Section>
  );
}

/** Soʻnggi natija hero + fanlar boʻyicha qatorlar. */
function LatestResult({ summary }: { summary: ResultSummary }) {
  const { data } = useResult(summary.id);
  const pct = Math.round(summary.percent);
  return (
    <>
      <Link to={`/results/${summary.id}`} className="bd-hero block px-4! py-4! no-underline">
        <div className="row gap-3.5!">
          <Ring percent={pct} size="lg" hero label={`${pct} foiz`}>
            {pct}%
          </Ring>
          <div className="grow">
            <div className="t-over opacity-85">Soʻnggi natija</div>
            <div className="t-h2 truncate">{summary.examTitle}</div>
            <div className="t-sm opacity-85 tabular">
              {summary.correct}/{summary.total} · {formatDay(summary.completedAt)}
            </div>
          </div>
          <Icon name="chevR" />
        </div>
      </Link>

      {data && (
        <Section title="Fanlar boʻyicha" id="subj-title">
          <ul className="bd-card flex flex-col gap-2.5 px-4! py-3.5!">
            {SUBJECT_ORDER.map((code) => data.subjects.find((s) => s.subject === code))
              .filter((s) => s !== undefined)
              .map((s) => (
                <li key={s.subject} className={cn('row gap-2.5!', SUBJECTS[s.subject].tone)}>
                  <SubjectIcon subject={s.subject} size="sm" />
                  <span className="t-sm grow text-ink">{SUBJECTS[s.subject].short}</span>
                  <span className="bd-bar w-24" role="progressbar" aria-label={`${SUBJECTS[s.subject].short}: ${s.correct}/${s.total}`} aria-valuemin={0} aria-valuemax={s.total} aria-valuenow={s.correct}>
                    <i style={{ ['--p' as string]: Math.round(s.percent) }} />
                  </span>
                  <b className="t-xs tabular w-9 text-right">
                    {s.correct}/{s.total}
                  </b>
                </li>
              ))}
          </ul>
        </Section>
      )}
    </>
  );
}

/** “Soʻnggi faoliyat → Hammasi” shu sahifaga keladi: imtihonlardan tashqari oʻyinlar tarixi ham shu yerda. */
function GameHistory() {
  const { data } = useGameStatistics();
  if (!data || data.recent.length === 0) return null;
  return (
    <Section title="Oʻyinlar tarixi" id="games-history-title" link={{ to: '/activities/stats', label: 'Statistika' }}>
      <ul className="bd-card bd-list px-4! py-0.5!">
        {data.recent.slice(0, 6).map((r) => {
          const meta = CATEGORY_META[r.category];
          return (
            <li key={r.sessionId} className="p-0!">
              <Link
                to={`/activities/result/${r.sessionId}`}
                aria-label={`${r.title}, ${formatDay(r.completedAt)}, ${r.score + r.bonus} ball`}
                className={cn('bd-rowcard tap-card min-h-[52px] py-2.5 text-inherit no-underline', meta.tone)}
              >
                <span className="bd-tile">
                  <Icon name={meta.icon} />
                </span>
                <div className="grow">
                  <div className="t-h3 truncate">{r.title}</div>
                  <div className="t-xs faint">
                    {formatDay(r.completedAt)} · {meta.short}
                  </div>
                </div>
                <b className="t-h3 tabular">+{r.score + r.bonus} ⭐</b>
              </Link>
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

/** Dizayn: ScreenResultsProfile → “Natijalar” (boʻsh va toʻla holat). */
export default function ResultsHistoryPage() {
  const { data, isPending, isError, error, refetch } = useResults();
  const empty = data?.length === 0;
  const sorted = data ? [...data].sort((a, b) => b.completedAt.localeCompare(a.completedAt)) : [];

  return (
    <div>
      <PageTitle title="Natijalarim" subtitle={empty || isPending ? 'Imtihonlar va oʻyinlar tarixi.' : undefined} />

      {isPending && <Skeleton className="mt-3 h-28 rounded-[var(--radius-xl)]" />}
      {isError && <ErrorState error={error} onRetry={() => void refetch()} />}

      {empty && (
        <div className="lg:grid lg:grid-cols-[1.6fr_1fr] lg:items-start lg:gap-6">
          <div className="bd-card bd-card--cream mt-5 flex flex-col items-center px-5! py-6! text-center">
            <Mascot mood="oylayapti" size={112} />
            <h2 className="t-h2 mt-2">Hali natija yoʻq — lekin hammasi oldinda!</h2>
            <p className="t-sm muted mt-1">Birinchi imtihonni topshir — natijang, fanlar boʻyicha tahlil va sinfdagi oʻrning shu yerda chiqadi.</p>
            <Link to="/exam" className={buttonClass('primary', { className: 'mt-4' })}>
              Imtihonlarga oʻtish
              <Icon name="arrowR" />
            </Link>
          </div>
          <div className="lg:mt-5 lg:[&>.sec:first-child]:mt-0">
            <PracticeSuggestion />
            <GameHistory />
          </div>
        </div>
      )}

      {sorted.length > 0 && (
        <div className="mt-3 lg:grid lg:grid-cols-2 lg:items-start lg:gap-6">
          <div>
            <LatestResult summary={sorted[0]!} />
            <GameHistory />
          </div>
          <Section title="Imtihonlar tarixi" id="history-title" className="lg:mt-0">
            <ul className="bd-card bd-list px-4! py-0.5!">
              {sorted.map((r) => {
                const pct = Math.round(r.percent);
                return (
                  <li key={r.id} className="p-0!">
                    <Link to={`/results/${r.id}`} className="bd-rowcard tap-card min-h-[52px] py-2.5 text-inherit no-underline">
                      <Ring percent={pct} className="is-brand" label={`${pct} foiz`}>
                        {pct}%
                      </Ring>
                      <div className="grow">
                        <div className="t-h3 truncate">{r.examTitle}</div>
                        <div className="t-xs faint tabular">
                          {formatDay(r.completedAt)} · {r.correct}/{r.total}
                        </div>
                      </div>
                      <Icon name="chevR" size={18} className="text-ink-3" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Section>
        </div>
      )}
    </div>
  );
}
