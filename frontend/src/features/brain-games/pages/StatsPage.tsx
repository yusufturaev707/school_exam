import { Link } from 'react-router';
import { useGameStatistics } from '../hooks/useGames';
import { CATEGORY_META, CATEGORY_ORDER, CategoryIcon } from '../utils/meta';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Section, StatTile, StatTiles, TopBar } from '@/components/shared/design';
import { useMotivation } from '@/hooks/useMotivation';
import { formatDay } from '@/lib/date';
import { cn } from '@/lib/cn';

/** Dizayn: ScreenProgress → “Mening statistikam”. Faqat oʻz faoliyati — reyting yoʻq, hech kim bilan solishtirilmaydi. */
export default function StatsPage() {
  const { data, isPending, isError, error, refetch } = useGameStatistics();
  const { streak } = useMotivation();

  if (isPending) {
    return (
      <div className="flex flex-col gap-4 pt-14">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
      </div>
    );
  }
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const maxCat = Math.max(1, ...data.categories.map((c) => c.completed));
  const byCat = new Map(data.categories.map((c) => [c.category, c.completed]));

  return (
    <div>
      <TopBar title="Mening statistikam" back="/activities" />

      {data.totalCompleted === 0 ? (
        <EmptyState
          card
          title="Hali oʻyin oʻynamading"
          description="Birinchi oʻyinni yakunlaganingda, bu yerda oʻz yutuqlaringni koʻrasan."
          action={
            <Link to="/activities" className={buttonClass('primary')}>
              Oʻyin tanlash
              <Icon name="arrowR" />
            </Link>
          }
        />
      ) : (
        <div className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-6">
          <div>
            <StatTiles>
              <StatTile icon="check" value={data.totalCompleted} label="mashgʻulot" />
              <StatTile icon="star" value={data.totalScore} label="jami ball" tone="is-star" />
              <StatTile icon="fire" value={streak} label="kun seriya" tone="is-streak" />
            </StatTiles>

            <Section title="Yoʻnalishlar boʻyicha" id="dirs-stat">
              <ul className="bd-card flex flex-col gap-2.5 px-4! py-3.5!">
                {CATEGORY_ORDER.map((c) => {
                  const n = byCat.get(c) ?? 0;
                  return (
                    <li key={c} className={cn('row gap-2.5!', CATEGORY_META[c].tone)}>
                      <CategoryIcon category={c} size="sm" />
                      <span className="t-sm w-[84px] shrink-0 text-ink">{CATEGORY_META[c].short}</span>
                      <span
                        className="bd-bar grow"
                        role="progressbar"
                        aria-label={`${CATEGORY_META[c].title}: ${n} ta`}
                        aria-valuemin={0}
                        aria-valuemax={maxCat}
                        aria-valuenow={n}
                      >
                        <i style={{ ['--p' as string]: Math.round((n / maxCat) * 100) }} />
                      </span>
                      <b className="t-xs tabular w-4 text-right">{n}</b>
                    </li>
                  );
                })}
              </ul>
            </Section>

            <div className="bd-card bd-card--cream row mt-3 items-start! gap-2.5! px-3.5! py-3!">
              <Icon name="bulb" size={18} className="text-logic" />
              <p className="t-sm muted">Ballar faqat oʻz oʻsishingni koʻrsatadi — hech kim bilan solishtirilmaydi.</p>
            </div>
          </div>

          <div>
            <Section title="Oʻyinlar" id="games-stat" className="lg:mt-0">
              <ul className="bd-card bd-list px-4! py-0.5!">
                {data.games.map((g) => (
                  <li key={g.gameId} className={cn('bd-rowcard min-h-12', CATEGORY_META[g.category].tone)}>
                    <CategoryIcon category={g.category} />
                    <div className="grow">
                      <div className="t-h3">{g.title}</div>
                      <div className="t-xs faint">{g.completed > 0 ? `${g.completed} marta oʻynalgan` : 'Hali oʻynalmagan'}</div>
                    </div>
                    {g.bestScore !== null && (
                      <b className="t-h3 tabular">
                        {g.bestScore} <span className="font-semibold text-ink-3">/ {g.maxScore}</span>
                      </b>
                    )}
                  </li>
                ))}
              </ul>
            </Section>

            {data.recent.length > 0 && (
              <Section title="Faoliyat tarixi" id="recent-stat">
                <ul className="bd-card bd-list px-4! py-0.5!">
                  {data.recent.map((r) => (
                    <li key={r.sessionId} className="p-0!">
                      <Link to={`/activities/result/${r.sessionId}`} className={cn('bd-rowcard tap-card min-h-[52px] py-2.5 text-inherit no-underline', CATEGORY_META[r.category].tone)}>
                        <CategoryIcon category={r.category} />
                        <div className="grow">
                          <div className="t-h3 truncate">{r.title}</div>
                          <div className="t-xs faint">{formatDay(r.completedAt)}</div>
                        </div>
                        <b className="t-h3 tabular">+{r.score + r.bonus} ⭐</b>
                      </Link>
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
