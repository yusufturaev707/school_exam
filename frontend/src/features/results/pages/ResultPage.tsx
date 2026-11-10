import { useEffect, useRef } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import type { SubjectCode } from '@/types/subject';
import { useResult } from '../api/resultsApi';
import { overallHeadline } from '../utils/feedback';
import { SubjectResultCard } from '../components/SubjectResultCard';
import { QuestionReview } from '../components/QuestionReview';
import { ResultScore } from '../components/ResultScore';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { ErrorState } from '@/components/feedback/ErrorState';
import { Mascot } from '@/components/shared/Mascot';
import { SUBJECT_ORDER } from '@/components/shared/subjects';
import { Section, StatTile, StatTiles, TopBar } from '@/components/shared/design';
import { formatDateTime } from '@/lib/date';

/** Imtihon natijasi: hero (katta ball halqasi + xursand maskot), toʻgʻri/xato/javobsiz plitalari, fanlar, savollar tahlili. */
/** `?subject=` from a subject card; also accepts the design names (logic, lang). */
function subjectParam(raw: string | null): SubjectCode | undefined {
  const v = raw === 'logic' ? 'iq' : raw === 'lang' ? 'language' : raw;
  return v === 'math' || v === 'iq' || v === 'language' ? v : undefined;
}

export default function ResultPage() {
  const { resultId = '' } = useParams();
  const [params] = useSearchParams();
  const initialSubject = subjectParam(params.get('subject'));
  const { data, isPending, isError, error, refetch } = useResult(resultId);
  const reviewRef = useRef<HTMLDivElement>(null);

  // Came from a subject card: jump straight to that subject's questions.
  useEffect(() => {
    if (initialSubject && data) reviewRef.current?.scrollIntoView({ block: 'start' });
  }, [initialSubject, data]);

  if (isPending) {
    return (
      <div className="flex flex-col gap-4 pt-14">
        <Skeleton className="h-48 rounded-[var(--radius-xl)]" />
        <Skeleton className="h-20" />
        <Skeleton className="h-56" />
      </div>
    );
  }
  if (isError)
    return (
      <>
        <TopBar title="Natija" back="/results" preferHistory />
        <ErrorState error={error} onRetry={() => void refetch()} fallback={{ to: '/results', label: 'Natijalarga qaytish' }} />
      </>
    );

  const { totals } = data;
  const headline = overallHeadline(totals.percent);
  const subjects = SUBJECT_ORDER.map((s) => data.subjects.find((x) => x.subject === s)).filter((x) => x !== undefined);

  return (
    <div>
      <TopBar title="Natija" back="/results" preferHistory />

      <section className="bd-hero lg:p-6!" aria-labelledby="result-title">
        <div className="pr-24 lg:pr-44">
          <span className="bd-chip bd-chip--status">
            <Icon name="check" size={14} />
            Topshirildi
          </span>
          <h1 id="result-title" className="t-hero mt-2">
            {headline.title}
          </h1>
          <p className="t-sm mt-1 opacity-88">{headline.text}</p>
        </div>
        <div className="mt-5">
          <ResultScore totals={totals} examTitle={data.examTitle} />
        </div>
        <p className="t-xs mt-1.5 flex items-center justify-center gap-1.5 text-center opacity-80">
          <Icon name="calendar" size={14} />
          {formatDateTime(data.completedAt)}
          {data.finishReason === 'timeout' && ' · vaqt tugaganda yakunlangan'}
        </p>
        <span className="bd-hero__mascot top-3 bottom-auto!">
          <Mascot mood="xursand" className="h-[92px] w-auto lg:h-[140px]" />
        </span>
      </section>

      <StatTiles className="mt-3">
        <StatTile icon="check" value={totals.correct} label="toʻgʻri" tone="is-success" />
        <StatTile icon="x" value={totals.incorrect} label="xato" tone="is-danger" />
        <StatTile icon="help" value={totals.unanswered} label="javobsiz" tone="is-muted" />
      </StatTiles>

      <Section title="Fanlar boʻyicha tahlil" id="subjects-heading">
        <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {subjects.map((s) => (
            <SubjectResultCard key={s.subject} result={s} />
          ))}
        </ul>
        <div className="bd-card bd-card--cream row mt-3 items-start! gap-2.5! px-3.5! py-3!">
          <Icon name="bulb" size={18} className="text-logic" />
          <p className="t-sm muted">Mantiq (IQ) savollari natijasi — bu faqat shu kungi mashq koʻrsatkichi. U aqlingizni oʻlchamaydi va mashq bilan albatta oʻsadi.</p>
        </div>
      </Section>

      <Section title="Savollar tahlili" id="review-heading">
        <div ref={reviewRef} className="scroll-mt-4" />
        {data.review.enabled && data.review.items && data.review.items.length > 0 ? (
          <QuestionReview items={data.review.items} initialSubject={initialSubject} />
        ) : (
          <div className="bd-card bd-card--flat row items-start! gap-3!">
            <Icon name="lock" className="text-ink-3" />
            <p className="t-sm muted">Bu imtihon uchun savollar va toʻgʻri javoblar hozircha yopiq. Umumiy natijangiz yuqorida koʻrsatilgan.</p>
          </div>
        )}
      </Section>

      <Link to="/" className={buttonClass('ghost', { fullWidth: true, className: 'mt-4' })}>
        <Icon name="home" />
        Bosh sahifaga qaytish
      </Link>
    </div>
  );
}
