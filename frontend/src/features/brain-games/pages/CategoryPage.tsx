import { Link, useParams } from 'react-router';
import { gameCategorySchema } from '../types';
import { useGameCategories, useGameStatistics, useGamesList } from '../hooks/useGames';
import { GameCard } from '../components/GameCard';
import { GameCategoryTabs } from '../components/GameCategoryTabs';
import { CATEGORY_META, CategoryIcon } from '../utils/meta';
import { Skeleton } from '@/components/ui/Skeleton';
import { buttonClass } from '@/components/ui/Button';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Section, TopBar } from '@/components/shared/design';
import { cn } from '@/lib/cn';

export default function CategoryPage() {
  const parsed = gameCategorySchema.safeParse(useParams().category);
  const games = useGamesList();
  const categories = useGameCategories();
  const stats = useGameStatistics();
  if (!parsed.success)
    return (
      <div>
        <TopBar title="Laboratoriya" back="/activities" preferHistory />
        <EmptyState
          card
          title="Bunday yoʻnalish topilmadi"
          description="Balki havola notoʻgʻri yozilgandir. Laboratoriyadagi yoʻnalishlardan birini tanlang."
          action={
            <Link to="/activities" className={buttonClass('primary')}>
              Laboratoriyaga qaytish
            </Link>
          }
        />
      </div>
    );
  const category = parsed.data;
  const meta = CATEGORY_META[category];
  const info = categories.data?.find((c) => c.id === category);
  const list = (games.data ?? []).filter((g) => g.category === category);
  const active = list.filter((g) => g.isActive);
  const soon = list.filter((g) => !g.isActive);
  const best = new Map(stats.data?.games.map((g) => [g.gameId, g.bestScore]) ?? []);

  return (
    <div>
      <TopBar title="Laboratoriya" back="/activities" preferHistory />
      {categories.data && <GameCategoryTabs categories={categories.data} active={category} layout="strip" />}

      <header className={cn('bd-dir mt-3 min-h-0! flex-row! items-center gap-3! p-4!', meta.tone)}>
        <CategoryIcon category={category} size="lg" className="bg-card!" />
        <div>
          <h1 className="t-hero text-[var(--ci)]">{meta.title}</h1>
          {info && <p className="t-sm text-[var(--ci)] opacity-85">{info.description}</p>}
        </div>
      </header>

      {games.isPending ? (
        <div className="mt-6 flex flex-col gap-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : games.isError ? (
        <ErrorState error={games.error} onRetry={() => void games.refetch()} />
      ) : list.length === 0 ? (
        <EmptyState
          card
          className="mt-6"
          title="Bu yoʻnalishda oʻyinlar tez orada!"
          description="Hozircha boshqa yoʻnalishlardagi oʻyinlarni sinab koʻring."
          action={
            <Link to="/activities" className={buttonClass('primary')}>
              Laboratoriyaga qaytish
            </Link>
          }
        />
      ) : (
        <>
          {active.length > 0 && (
            <Section title="Oʻyinlar" id="cat-games">
              <ul className="grid gap-2 lg:grid-cols-2">
                {active.map((g) => (
                  <li key={g.id}>
                    <GameCard game={g} bestScore={best.get(g.id)} />
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {soon.length > 0 && (
            <Section title="Tez orada" id="cat-soon">
              <ul className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                {soon.map((g) => (
                  <li key={g.id}>
                    <GameCard game={g} compact />
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </>
      )}
    </div>
  );
}
