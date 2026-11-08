import type { Answers, Question } from '../types';
import { SUBJECTS, SUBJECT_ORDER, SubjectIcon } from '@/components/shared/subjects';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

interface Props {
  questions: Question[];
  answers: Answers;
  currentIndex: number;
  onSelect: (index: number) => void;
}

/** Grid of question buttons grouped by subject. States use shape + icon + colour. */
export function QuestionNavigator({ questions, answers, currentIndex, onSelect }: Props) {
  const groups = SUBJECT_ORDER.map((subject) => ({
    subject,
    items: questions.map((q, index) => ({ q, index })).filter(({ q }) => q.subject === subject),
  })).filter((g) => g.items.length > 0);

  return (
    <nav aria-label="Savollar roʻyxati" className="flex flex-col gap-5">
      {groups.map(({ subject, items }) => {
        const answered = items.filter(({ q }) => (answers[q.id]?.length ?? 0) > 0).length;
        return (
          <section key={subject} aria-label={SUBJECTS[subject].title}>
            <div className="row mb-2.5">
              <SubjectIcon subject={subject} size="sm" />
              <h3 className="t-h3">{SUBJECTS[subject].short}</h3>
              <span className="t-xs muted tabular ml-auto">
                {answered}/{items.length}
              </span>
            </div>
            <ol className="grid grid-cols-5 gap-2">
              {items.map(({ q, index }, i) => {
                const isAnswered = (answers[q.id]?.length ?? 0) > 0;
                const isCurrent = index === currentIndex;
                return (
                  <li key={q.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(index)}
                      aria-current={isCurrent ? 'step' : undefined}
                      aria-label={`${i + 1}-savol, ${isAnswered ? 'javob belgilangan' : 'javob berilmagan'}${isCurrent ? ', hozirgi savol' : ''}`}
                      className={cn(
                        'tabular relative flex h-11 w-full items-center justify-center rounded-[var(--radius-sm)] text-[15px] font-extrabold transition-[transform,background-color] active:scale-95',
                        isAnswered ? 'bg-brand text-on-brand' : 'bg-card text-ink-2 shadow-[inset_0_0_0_1.5px_var(--line)]',
                        isCurrent && 'ring-3 ring-sun ring-offset-2 ring-offset-card',
                      )}
                    >
                      {i + 1}
                      {isAnswered && (
                        <span className="absolute -top-1.5 -right-1.5 flex size-4.5 items-center justify-center rounded-full bg-card text-brand shadow-sm" aria-hidden="true">
                          <Icon name="check" size={12} />
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ol>
          </section>
        );
      })}

      <ul className="t-xs muted flex flex-wrap gap-x-4 gap-y-2" aria-label="Belgilar">
        <li className="flex items-center gap-1.5">
          <span className="size-4 rounded-md bg-brand" aria-hidden="true" /> Javob berilgan
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-4 rounded-md shadow-[inset_0_0_0_1.5px_var(--line)]" aria-hidden="true" /> Javobsiz
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-4 rounded-md ring-2 ring-sun ring-offset-1" aria-hidden="true" /> Hozirgi
        </li>
      </ul>
    </nav>
  );
}
