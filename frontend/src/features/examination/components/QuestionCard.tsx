import { AnimatePresence, motion } from 'motion/react';
import type { Question } from '../types';
import { RichContent } from '@/components/shared/RichContent';
import { SUBJECTS, SubjectIcon } from '@/components/shared/subjects';
import { Icon } from '@/components/ui/Icon';
import { getQuestionRenderer } from './questionRenderers';
import { cn } from '@/lib/cn';

interface Props {
  question: Question;
  /** Position within its subject, e.g. 3 of 15. */
  subjectIndex: number;
  subjectTotal: number;
  selected: string[];
  disabled: boolean;
  onSelect: (optionId: string) => void;
}

/** Dizayn: QuestionCard — fan plitasi + “3-savol / 15”, savol matni (body, 800), javob kartalari. */
export function QuestionCard({ question, subjectIndex, subjectTotal, selected, disabled, onSelect }: Props) {
  const Renderer = getQuestionRenderer(question.type);
  const subject = SUBJECTS[question.subject];
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.article
        key={question.id}
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -16 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
        aria-labelledby={`q-${question.id}-heading`}
        className="bd-card p-4! md:p-6!"
      >
        <header className="row gap-2.5!">
          <SubjectIcon subject={question.subject} />
          <div className="grow">
            <h2 id={`q-${question.id}-heading`} className="t-h3">
              {subjectIndex}-savol <span className="muted font-semibold">/ {subjectTotal}</span>
            </h2>
            <p className={cn('t-xs', subject.ink)}>{subject.title}</p>
          </div>
          <span className="bd-chip bd-chip--soft tabular hidden sm:inline-flex">№ {question.number}</span>
        </header>

        {question.passage && question.passage.length > 0 && (
          <section aria-label="Matn" className="bd-card--cream mt-4 rounded-[var(--radius-md)] p-4 text-[15px] leading-relaxed shadow-[inset_0_0_0_1px_var(--line)] md:text-[16px]">
            <p className="t-over muted mb-2 flex items-center gap-1.5">
              <Icon name="book" size={16} />
              Matnni diqqat bilan oʻqi
            </p>
            <RichContent blocks={question.passage} />
          </section>
        )}

        <div id={`q-${question.id}-prompt`} className="mt-4 text-[18px] leading-snug font-extrabold md:text-[20px]">
          <RichContent blocks={question.prompt} />
        </div>

        <div className="mt-4 md:mt-5">
          <Renderer question={question} selected={selected} disabled={disabled} onSelect={onSelect} />
        </div>
      </motion.article>
    </AnimatePresence>
  );
}
