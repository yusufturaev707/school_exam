import { useState } from 'react';
import type { ReviewItem } from '../types';
import type { SubjectCode } from '@/types/subject';
import { RichContent, InlineContent } from '@/components/shared/RichContent';
import { SUBJECTS, SUBJECT_ORDER } from '@/components/shared/subjects';
import { Icon, type IconName } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

function statusOf(item: ReviewItem): 'correct' | 'incorrect' | 'unanswered' {
  if (item.selectedOptionIds.length === 0) return 'unanswered';
  const ok = item.selectedOptionIds.length === item.correctOptionIds.length && item.selectedOptionIds.every((id) => item.correctOptionIds.includes(id));
  return ok ? 'correct' : 'incorrect';
}

const STATUS: Record<'correct' | 'incorrect' | 'unanswered', { label: string; icon: IconName; tone: string }> = {
  correct: { label: 'Toʻgʻri', icon: 'check', tone: 'is-success' },
  incorrect: { label: 'Xato', icon: 'x', tone: 'is-danger' },
  unanswered: { label: 'Javobsiz', icon: 'help', tone: 'is-muted' },
};

function ReviewCard({ item }: { item: ReviewItem }) {
  const status = statusOf(item);
  const s = STATUS[status];
  return (
    <details className="group bd-card p-0! [&_summary::-webkit-details-marker]:hidden">
      <summary className="bd-rowcard tap-card cursor-pointer list-none rounded-[var(--radius-lg)] px-4 py-2 hover:bg-bg-tint">
        <span className={cn('bd-tile', s.tone)} aria-hidden="true">
          <Icon name={s.icon} size={18} />
        </span>
        <span className="grow">
          <span className="t-h3 block">
            {item.number}-savol · <span className={SUBJECTS[item.subject].ink}>{SUBJECTS[item.subject].short}</span>
          </span>
          <span className="t-xs faint block">{s.label}</span>
        </span>
        <Icon name="chevD" size={18} className="text-ink-3 transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t border-line px-4 pt-4 pb-5">
        {item.passage && <RichContent blocks={item.passage} className="bd-card--cream mb-3 rounded-[var(--radius-md)] p-3 text-[15px] shadow-[inset_0_0_0_1px_var(--line)]" />}
        <RichContent blocks={item.prompt} className="text-[16px] leading-relaxed font-medium" />
        <ul className="mt-3 flex flex-col gap-2">
          {item.options.map((o) => {
            const correct = item.correctOptionIds.includes(o.id);
            const chosen = item.selectedOptionIds.includes(o.id);
            return (
              <li
                key={o.id}
                className={cn(
                  'flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-[15px]',
                  correct ? 'bg-success-soft shadow-[inset_0_0_0_2px_var(--success)]' : chosen ? 'bg-danger-soft shadow-[inset_0_0_0_2px_var(--danger)]' : 'shadow-[inset_0_0_0_1.5px_var(--line)]',
                )}
              >
                <span className="w-5 font-black text-ink-3">{o.label}</span>
                <span className="min-w-0 flex-1 font-bold">
                  <InlineContent blocks={o.content} displayStyle />
                </span>
                {correct && (
                  <span className="t-xs inline-flex items-center gap-1 text-success-ink">
                    <Icon name="check" size={16} /> Toʻgʻri javob
                  </span>
                )}
                {chosen && !correct && (
                  <span className="t-xs inline-flex items-center gap-1 text-danger-ink">
                    <Icon name="x" size={16} /> Sening javobing
                  </span>
                )}
                {chosen && correct && <span className="sr-only">(sening javobing)</span>}
              </li>
            );
          })}
        </ul>
        {item.explanation && item.explanation.length > 0 && (
          <div className="t-sm mt-3 flex gap-2.5 rounded-[var(--radius-md)] bg-logic-soft p-3 text-ink">
            <Icon name="bulb" size={18} className="text-logic-ink" />
            <RichContent blocks={item.explanation} />
          </div>
        )}
      </div>
    </details>
  );
}

type StatusFilter = 'all' | 'incorrect' | 'unanswered' | 'correct';

export function QuestionReview({ items, initialSubject }: { items: ReviewItem[]; initialSubject?: SubjectCode }) {
  const [subject, setSubject] = useState<SubjectCode | 'all'>(initialSubject ?? 'all');
  const [status, setStatus] = useState<StatusFilter>('all');

  const bySubject = subject === 'all' ? items : items.filter((i) => i.subject === subject);
  const visible = status === 'all' ? bySubject : bySubject.filter((i) => statusOf(i) === status);
  const count = (s: StatusFilter) => (s === 'all' ? bySubject.length : bySubject.filter((i) => statusOf(i) === s).length);

  const subjectChips: Array<{ id: SubjectCode | 'all'; label: string }> = [{ id: 'all', label: 'Hammasi' }, ...SUBJECT_ORDER.map((s) => ({ id: s, label: SUBJECTS[s].short }))];
  const statusChips: Array<{ id: StatusFilter; label: string }> = [
    { id: 'all', label: 'Barchasi' },
    { id: 'incorrect', label: 'Xatolar' },
    { id: 'unanswered', label: 'Javobsiz' },
    { id: 'correct', label: 'Toʻgʻri' },
  ];

  return (
    <div>
      <div role="group" aria-label="Fan boʻyicha saralash" className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 py-1">
        {subjectChips.map((c) => (
          <button key={c.id} type="button" aria-pressed={subject === c.id} onClick={() => setSubject(c.id)} className={cn('bd-chip bd-chip--filter shrink-0', subject === c.id && 'is-on')}>
            {c.label}
          </button>
        ))}
      </div>

      <div role="group" aria-label="Natija boʻyicha saralash" className="bd-seg mt-3 grid-cols-4!">
        {statusChips.map((c) => (
          <button key={c.id} type="button" aria-pressed={status === c.id} onClick={() => setStatus(c.id)} className={cn(status === c.id && 'is-on')}>
            {c.label}
            <span className="tabular text-[11px] opacity-75">{count(c.id)}</span>
          </button>
        ))}
      </div>

      <div className="mt-3 flex flex-col gap-2">
        {visible.length === 0 ? <p className="bd-card t-sm muted p-5! text-center">Bu boʻlimda savol yoʻq.</p> : visible.map((item) => <ReviewCard key={item.questionId} item={item} />)}
      </div>
    </div>
  );
}
