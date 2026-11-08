import { Link } from 'react-router';
import type { ExamSummary } from '../types';
import { Icon, type IconName } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { Ring } from '@/components/ui/CircularProgress';
import { Mascot } from '@/components/shared/Mascot';
import { formatDateTime } from '@/lib/date';
import { cn } from '@/lib/cn';

const STATUS: Record<ExamSummary['status'], { label: string; icon: IconName }> = {
  available: { label: 'Topshirish mumkin', icon: 'sparkle' },
  in_progress: { label: 'Davom etmoqda', icon: 'clock' },
  completed: { label: 'Topshirildi', icon: 'check' },
  unavailable: { label: 'Hali ochilmagan', icon: 'lock' },
};

export function ExamStatusChip({ status }: { status: ExamSummary['status'] }) {
  const s = STATUS[status];
  return (
    <span className={cn('bd-chip bd-chip--status', status === 'unavailable' && 'bg-white/16! text-on-hero!')}>
      <Icon name={s.icon} size={14} />
      {s.label}
    </span>
  );
}

export function examCta(exam: ExamSummary): { to: string; label: string; icon: IconName } | null {
  if (exam.status === 'completed' && exam.resultId) return { to: `/results/${exam.resultId}`, label: 'Natijani koʻrish', icon: 'arrowR' };
  if (exam.status === 'in_progress' && exam.activeAttemptId) return { to: `/exam/attempt/${exam.activeAttemptId}`, label: 'Davom ettirish', icon: 'play' };
  if (exam.status === 'available') return { to: `/exam/${exam.id}`, label: 'Imtihonni boshlash', icon: 'arrowR' };
  return null;
}

/**
 * Dizayn: ExamHero (bd-hero) — ekranning eng koʻzga tashlanadigan bloki (≤35% balandlik).
 * Maskot tugmaning oʻng tomonida unga ishora qiladi; topshirilgan boʻlsa — natija halqasi va xursand maskot.
 */
export function ExamCard({ exam, score, className }: { exam: ExamSummary; score?: { correct: number; total: number; caption?: string } | null; className?: string }) {
  const cta = examCta(exam);
  const done = exam.status === 'completed' && score;
  const pct = done ? Math.round((score.correct / score.total) * 100) : 0;

  return (
    <section aria-labelledby={`exam-${exam.id}`} className={cn('bd-hero lg:min-h-[220px] lg:p-6!', className)}>
      <ExamStatusChip status={exam.status} />
      <h2 id={`exam-${exam.id}`} className="t-hero bd-hero__title lg:mt-3! lg:max-w-[420px]! lg:text-[32px] lg:leading-[38px] lg:font-black">
        {exam.title}
      </h2>
      {exam.description && <p className="t-body mt-1 hidden max-w-[460px] opacity-88 lg:block">{exam.description}</p>}

      {done ? (
        <div className="bd-hero__score">
          <Ring percent={pct} size="lg" hero label={`${pct} foiz`}>
            {pct}%
          </Ring>
          <div>
            <div className="t-stat tabular">
              {score.correct}/{score.total}
            </div>
            {score.caption && <div className="t-sm opacity-85">{score.caption}</div>}
          </div>
        </div>
      ) : (
        <div className="bd-hero__meta">
          <span className="bd-chip bd-chip--glass">
            <Icon name="list" size={16} />
            {exam.totalQuestions} ta savol
          </span>
          <span className="bd-chip bd-chip--glass">
            <Icon name="clock" size={16} />
            {exam.durationMinutes} daqiqa
          </span>
        </div>
      )}

      {cta ? (
        <Link to={cta.to} className={buttonClass('light', { className: 'bd-hero__cta' })}>
          {cta.label}
          <Icon name={cta.icon} />
        </Link>
      ) : (
        <p className="t-sm mt-4 max-w-[220px] rounded-[var(--radius-md)] bg-white/12 px-3 py-2.5 lg:max-w-[420px]">
          {exam.availableFrom ? `Imtihon ${formatDateTime(exam.availableFrom)} da ochiladi.` : 'Imtihon hali ochilmagan. Tez orada!'}
        </p>
      )}

      <span className="bd-hero__mascot lg:right-8! lg:bottom-3!">
        <Mascot mood={done ? 'xursand' : cta ? 'ishora' : 'oylayapti'} className="h-[92px] w-auto lg:h-[150px]" />
      </span>
    </section>
  );
}
