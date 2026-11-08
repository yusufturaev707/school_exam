import { useState } from 'react';
import { Link } from 'react-router';
import { useAvailableExams } from '../hooks/useExams';
import type { ExamSummary } from '../types';
import { ExamStatusChip, examCta } from '../components/ExamCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { PageTitle, Section } from '@/components/shared/design';
import { SUBJECTS } from '@/components/shared/subjects';
import { formatDay } from '@/lib/date';
import { cn } from '@/lib/cn';

type Filter = 'all' | 'open' | 'upcoming' | 'done';

/** Ochiq imtihon kartasi (ScreenExams). */
function OpenExamCard({ exam }: { exam: ExamSummary }) {
  const cta = examCta(exam);
  return (
    <Link to={cta?.to ?? `/exam/${exam.id}`} className="bd-card bd-tap tap-card block px-4! py-3.5! text-inherit no-underline">
      <div className="row">
        <ExamStatusChip status={exam.status} />
      </div>
      <div className="t-h2 mt-2">{exam.title}</div>
      <div className="row mt-2 flex-wrap gap-1.5!">
        {exam.sections.map((s) => (
          <span key={s.subject} className={cn('bd-chip bd-chip--soft', SUBJECTS[s.subject].tone)} aria-label={`${SUBJECTS[s.subject].short}: ${s.questionCount} ta savol`}>
            <Icon name={SUBJECTS[s.subject].icon} size={14} />
            {s.questionCount}
          </span>
        ))}
        <span className="t-sm muted">· {exam.durationMinutes} daqiqa</span>
      </div>
      <div className="row mt-3 text-brand-ink">
        <span className="t-sm grow font-extrabold!">{exam.status === 'in_progress' ? 'Davom ettirish' : 'Batafsil koʻrish'}</span>
        <Icon name="arrowR" />
      </div>
    </Link>
  );
}

function UpcomingRow({ exam, i }: { exam: ExamSummary; i: number }) {
  const date = exam.availableFrom ? formatDay(exam.availableFrom) : null;
  return (
    <div className={cn('bd-card bd-card--flat bd-rowcard', i % 2 ? 'is-spatial' : 'is-attn')}>
      <span className="bd-tile">
        <Icon name={i % 2 ? 'calendar' : 'trophy'} />
      </span>
      <div className="grow">
        <div className="t-h3">{exam.title}</div>
        <div className="t-xs faint">
          {date ? `${date} da ochiladi · ` : ''}
          {exam.totalQuestions} ta savol
        </div>
      </div>
      <span className="bd-chip bd-chip--soft">
        <Icon name="lock" size={14} />
        {date ?? 'Tez orada'}
      </span>
    </div>
  );
}

function DoneRow({ exam }: { exam: ExamSummary }) {
  return (
    <Link to={exam.resultId ? `/results/${exam.resultId}` : '/results'} className="bd-card bd-rowcard bd-tap tap-card is-brand text-inherit no-underline">
      <span className="bd-tile">
        <Icon name="check" />
      </span>
      <div className="grow">
        <div className="t-h3">{exam.title}</div>
        <div className="t-xs faint">Topshirilgan · {exam.totalQuestions} ta savol</div>
      </div>
      <Icon name="chevR" size={18} className="text-ink-3" />
    </Link>
  );
}

/** Dizayn: ScreenExams — filtr chiplari, “Ochiq / Kelgusi / Topshirilgan” boʻlimlari. */
export default function ExamListPage() {
  const { data, isPending, isError, error, refetch } = useAvailableExams();
  const [filter, setFilter] = useState<Filter>('all');

  const open = data?.filter((e) => e.status === 'available' || e.status === 'in_progress') ?? [];
  const upcoming = data?.filter((e) => e.status === 'unavailable') ?? [];
  const done = data?.filter((e) => e.status === 'completed') ?? [];

  const chips: Array<{ id: Filter; label: string; n?: number }> = [
    { id: 'all', label: 'Hammasi' },
    { id: 'open', label: 'Ochiq', n: open.length },
    { id: 'upcoming', label: 'Kelgusi', n: upcoming.length },
    { id: 'done', label: 'Topshirilgan', n: done.length },
  ];
  const show = (f: Filter) => filter === 'all' || filter === f;

  return (
    <div>
      <PageTitle title="Imtihonlar" subtitle="Senga ochiq imtihonlar shu yerda." />
      <div className="no-scrollbar -mx-4 mt-4 mb-1 flex gap-2 overflow-x-auto px-4 py-1" role="group" aria-label="Filtr">
        {chips
          .filter((c) => c.id === 'all' || (c.n ?? 0) > 0)
          .map((c) => (
            <button key={c.id} type="button" aria-pressed={filter === c.id} onClick={() => setFilter(c.id)} className={cn('bd-chip bd-chip--filter shrink-0', filter === c.id && 'is-on')}>
              {c.label}
              {c.n !== undefined && ` · ${c.n}`}
            </button>
          ))}
      </div>

      {isPending && <Skeleton className="mt-6 h-44" />}
      {isError && <ErrorState error={error} onRetry={() => void refetch()} />}
      {data?.length === 0 && <EmptyState card className="mt-5" title="Hozircha imtihon yoʻq" description="Yangi imtihon ochilganda shu yerda paydo boʻladi." />}

      <div className="lg:grid lg:grid-cols-2 lg:gap-x-6">
        {show('open') && open.length > 0 && (
          <Section title="Ochiq" id="open-title">
            <div className="flex flex-col gap-2">
              {open.map((e) => (
                <OpenExamCard key={e.id} exam={e} />
              ))}
            </div>
          </Section>
        )}
        {show('upcoming') && upcoming.length > 0 && (
          <Section title="Kelgusi" id="upcoming-title">
            <div className="flex flex-col gap-2">
              {upcoming.map((e, i) => (
                <UpcomingRow key={e.id} exam={e} i={i} />
              ))}
            </div>
          </Section>
        )}
        {show('done') && done.length > 0 && (
          <Section title="Topshirilgan" id="done-title">
            <div className="flex flex-col gap-2">
              {done.map((e) => (
                <DoneRow key={e.id} exam={e} />
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
