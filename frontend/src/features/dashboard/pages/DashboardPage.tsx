import { useDashboard } from '../api/dashboardApi';
import { SubjectCard } from '../components/SubjectCard';
import { RecentActivity, buildActivity } from '../components/RecentActivity';
import { MissionCard } from '../components/MissionCard';
import { DailyQuestion } from '../components/DailyQuestion';
import { ExamCard } from '@/features/examination/components/ExamCard';
import { BadgeRow, badgeSummary, sortAchievements } from '@/features/brain-games/components/AchievementCard';
import { useAchievements, useDailyChallenge, useGameStatistics } from '@/features/brain-games/hooks/useGames';
import { AppHeader } from '@/components/shared/AppHeader';
import { SectionHead } from '@/components/shared/design';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { SUBJECT_ORDER } from '@/components/shared/subjects';
import { formatDay } from '@/lib/date';

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-3 pt-14 lg:pt-0" aria-busy="true" aria-label="Yuklanmoqda">
      <Skeleton className="h-60 rounded-[var(--radius-xl)]" />
      <Skeleton className="h-16" />
      <div className="mt-6 grid grid-cols-3 gap-2">
        <Skeleton className="h-26" />
        <Skeleton className="h-26" />
        <Skeleton className="h-26" />
      </div>
    </div>
  );
}

/*
 * Dizayn: ScreenHome (telefon) + ScreenHomeDesktop (≥1024px, 1.6fr / 1fr).
 * Telefonda tartib: hero → missiya → fanlar → yutuqlar → kun savoli / soʻnggi faoliyat.
 * Kompyuterda chap ustun: hero, fanlar, faoliyat; oʻng: missiya, yutuqlar, kun savoli.
 */
export default function DashboardPage() {
  const { data, isPending, isError, error, refetch } = useDashboard();
  const daily = useDailyChallenge();
  const achievements = useAchievements();
  const stats = useGameStatistics();

  if (isPending)
    return (
      <>
        <AppHeader />
        <DashboardSkeleton />
      </>
    );
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const mainExam = data.examinations.find((e) => e.status === 'in_progress') ?? data.examinations.find((e) => e.status === 'available') ?? data.examinations[0];
  const sections = mainExam?.sections ?? [];
  const lastResult = mainExam?.resultId ? data.recentActivity.find((r) => r.resultId === mainExam.resultId) : undefined;
  const activity = buildActivity(data.recentActivity, stats.data?.recent);
  const isNew = activity.length === 0;

  const sortedBadges = achievements.data ? sortAchievements(achievements.data) : [];
  const { unlocked, available } = badgeSummary(achievements.data);
  const nextBadge = sortedBadges.find((a) => !a.unlockedAt && !a.comingSoon);

  const hero = mainExam ? (
    <ExamCard
      exam={mainExam}
      score={lastResult ? { correct: lastResult.correct, total: lastResult.total, caption: formatDay(lastResult.completedAt) } : null}
    />
  ) : (
    <EmptyState card title="Hozircha imtihon yoʻq" description="Yangi imtihon ochilganda shu yerda koʻrinadi. Bu orada bilimlar laboratoriyasiga kirib koʻring!" />
  );

  const mission = daily.data ? (
    <div className="mt-3 lg:mt-0">
      <MissionCard daily={daily.data} />
    </div>
  ) : daily.isPending ? (
    <Skeleton className="mt-3 h-16 lg:mt-0" />
  ) : null;

  const subjects =
    sections.length > 0 ? (
      <section className="sec lg:mt-0" aria-labelledby="subjects-title">
        <SectionHead title="Imtihon fanlari" id="subjects-title" link={{ to: '/exam', label: 'Barchasi' }} desktopLarge />
        <div className="bd-subjects lg:gap-4!">
          {SUBJECT_ORDER.map((code) => {
            const s = sections.find((x) => x.subject === code);
            if (!s) return null;
            const percent = lastResult ? (data.stats.subjects.find((x) => x.subject === code)?.percent ?? null) : null;
            // Completed exam → its result with this subject pre-selected; otherwise the exam's detail page.
            const to = mainExam?.status === 'completed' && mainExam.resultId ? `/results/${mainExam.resultId}?subject=${code}` : mainExam ? `/exam/${mainExam.id}` : '/exam';
            return <SubjectCard key={code} subject={code} questionCount={s.questionCount} percent={percent} to={to} />;
          })}
        </div>
      </section>
    ) : null;

  const badges = achievements.data ? (
    <section className="sec lg:mt-0" aria-labelledby="badges-title">
      <SectionHead title="Yutuqlarim" id="badges-title" link={{ to: '/activities/achievements', label: `${unlocked}/${available}` }} desktopLarge />
      <div className="bd-card px-3! pt-3.5! pb-3! lg:py-4!">
        <BadgeRow achievements={sortedBadges} />
        {nextBadge && (
          <p className="t-sm muted mt-2.5 text-center">
            {unlocked === 0 ? 'Birinchi oʻyinni yakunlang — birinchi nishon sizniki!' : `Keyingi nishon: «${nextBadge.title}» — ${nextBadge.description.toLowerCase()}`}
          </p>
        )}
      </div>
    </section>
  ) : null;

  const recent = (
    <section className={isNew ? 'sec hidden' : 'sec lg:mt-0'} aria-labelledby="recent-title">
      <SectionHead title="Soʻnggi faoliyat" id="recent-title" link={{ to: '/results', label: 'Hammasi' }} desktopLarge />
      <RecentActivity rows={activity} />
    </section>
  );

  const question = (
    <section className={isNew ? 'sec lg:mt-0' : 'sec hidden lg:block lg:mt-0'} aria-labelledby="question-title">
      <SectionHead title="Kun savoli" id="question-title" desktopLarge />
      <DailyQuestion />
    </section>
  );

  return (
    <>
      <AppHeader />
      <div className="bd-rise flex flex-col lg:grid lg:grid-cols-[1.6fr_1fr] lg:items-start lg:gap-6">
        <div className="contents lg:flex lg:flex-col lg:gap-6">
          <div className="order-1">{hero}</div>
          <div className="order-3">{subjects}</div>
          <div className="order-5">{recent}</div>
        </div>
        <div className="contents lg:flex lg:flex-col lg:gap-6">
          <div className="order-2">{mission}</div>
          <div className="order-4">{badges}</div>
          <div className="order-6">{question}</div>
        </div>
      </div>
    </>
  );
}
