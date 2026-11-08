import { useAchievements } from '../hooks/useGames';
import { AchievementCard, badgeSummary, sortAchievements } from '../components/AchievementCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { Mascot } from '@/components/shared/Mascot';
import { Section, TopBar } from '@/components/shared/design';

/** Dizayn: ScreenProgress → “Yutuqlarim”: xulosa kartasi + 3 ustunli nishon gridi. */
export default function AchievementsPage() {
  const { data, isPending, isError, error, refetch } = useAchievements();
  if (isPending) return <Skeleton className="mt-14 h-96" />;
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const { unlocked, available } = badgeSummary(data);
  const sorted = sortAchievements(data);
  const soon = data.length - available;
  const pct = available ? Math.round((unlocked / available) * 100) : 0;

  return (
    <div>
      <TopBar title="Yutuqlarim" back="/activities" preferHistory />

      <div className="bd-card row gap-3! px-4! py-3!">
        <Mascot mood={unlocked > 0 ? 'xursand' : 'oylayapti'} size={64} />
        <div className="grow">
          <div className="t-stat tabular">
            {unlocked} / {available}
          </div>
          <p className="t-sm muted">ta yutuq ochildi{soon > 0 ? ` · yana ${soon} tasi tez orada` : ''}</p>
          <span className="bd-bar mt-1.5 block" role="progressbar" aria-label="Ochilgan yutuqlar" aria-valuemin={0} aria-valuemax={available} aria-valuenow={unlocked}>
            <i style={{ ['--p' as string]: pct }} />
          </span>
        </div>
      </div>

      <Section title="Barcha nishonlar" id="all-badges">
        <div className="bd-badgegrid md:grid-cols-4! lg:grid-cols-6!">
          {sorted.map((a) => (
            <AchievementCard key={a.id} achievement={a} />
          ))}
        </div>
      </Section>
    </div>
  );
}
