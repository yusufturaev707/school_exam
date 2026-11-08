import { useAchievements, useDailyChallenge, useGameCategories, useGameStatistics, useGamesList } from '../hooks/useGames';
import { DailyChallengeCard } from '../components/DailyChallengeCard';
import { GameCard } from '../components/GameCard';
import { GameCategoryTabs } from '../components/GameCategoryTabs';
import { badgeSummary } from '../components/AchievementCard';
import { AppHeader } from '@/components/shared/AppHeader';
import { Section, StatTile, StatTiles } from '@/components/shared/design';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { useMotivation } from '@/hooks/useMotivation';
import { Link } from 'react-router';

/** Dizayn: ScreenGames → “Oʻyinlar / Laboratoriya”. */
export default function LabHomePage() {
  const games = useGamesList();
  const categories = useGameCategories();
  const daily = useDailyChallenge();
  const stats = useGameStatistics();
  const achievements = useAchievements();
  const { streak } = useMotivation();

  const { unlocked, available } = badgeSummary(achievements.data);
  const featured = games.data?.filter((g) => g.isActive) ?? [];
  const comingSoon = games.data?.filter((g) => !g.isActive) ?? [];
  const best = new Map(stats.data?.games.map((g) => [g.gameId, g.bestScore]) ?? []);

  return (
    <div>
      <AppHeader sub="Bilimlar laboratoriyasi" desktopSub="Bilimlar laboratoriyasi — bugun nimani kashf qilamiz?" />

      <div className="lg:grid lg:grid-cols-[1.6fr_1fr] lg:items-start lg:gap-6">
        <div>
          {daily.isPending ? <Skeleton className="h-44 rounded-[var(--radius-xl)]" /> : daily.data ? <DailyChallengeCard daily={daily.data} /> : null}

          <Link to="/activities/stats" className="tap-card mt-3 block no-underline" aria-label="Mening statistikam">
            <StatTiles>
              <StatTile icon="fire" value={streak} label="kun seriya" tone="is-streak" />
              <StatTile icon="star" value={stats.data?.totalScore ?? '–'} label="ball" tone="is-star" />
              <StatTile icon="trophy" value={achievements.data ? `${unlocked}/${available}` : '–'} label="yutuq" tone="is-memory" />
            </StatTiles>
          </Link>

          <Section title="Yoʻnalishlar" id="dirs-title">
            {categories.data ? <GameCategoryTabs categories={categories.data} /> : <Skeleton className="h-44" />}
          </Section>
        </div>

        <div>
          <Section title="Oʻyinlar" id="games-title" link={{ to: '/activities/stats', label: 'Statistika' }} className="lg:mt-0">
            {games.isPending ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </div>
            ) : games.isError ? (
              <ErrorState error={games.error} onRetry={() => void games.refetch()} />
            ) : (
              <ul className="flex flex-col gap-2">
                {featured.map((g) => (
                  <li key={g.id}>
                    <GameCard game={g} bestScore={best.get(g.id)} />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {comingSoon.length > 0 && (
            <Section title="Tez orada" id="soon-title">
              <ul className="grid grid-cols-2 gap-2">
                {comingSoon.map((g) => (
                  <li key={g.id}>
                    <GameCard game={g} compact />
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}
