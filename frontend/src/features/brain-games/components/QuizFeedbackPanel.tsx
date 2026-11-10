import { useMemo } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import type { AnswerResponse } from '../types';
import { CORRECT_LINES, WRONG_LINES, randomLine } from '../utils/feedback';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { Mascot } from '@/components/shared/Mascot';

interface Props {
  feedback: AnswerResponse | null;
  error: unknown;
  isLast: boolean;
  onNext: () => void;
}

/**
 * Dizayn: ScreenPlay — maskot pufagida qisqa ragʻbat. Toʻgʻrida xursand + “+10 ⭐”, xatoda hayron +
 * “Hech gap emas, yana bir bor!” — hech qachon ayblamaydi, doim tushuntiradi.
 */
export function QuizFeedbackPanel({ feedback, error, isLast, onNext }: Props) {
  const line = useMemo(() => (feedback ? randomLine(feedback.correct ? CORRECT_LINES : WRONG_LINES) : ''), [feedback]);

  return (
    <AnimatePresence>
      {(feedback !== null || error != null) && (
        <motion.div
          key={feedback?.questionId ?? 'error'}
          initial={{ y: 40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 40, opacity: 0, pointerEvents: 'none' }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="bd-sticky z-30! pt-3!"
        >
          <div className="bd-sticky__in">
            {feedback ? (
              <>
                {/* Only the verdict is a live region — a button inside a status region loses its name in some screen readers. */}
                <div className="row items-end! gap-2.5!" role="status" aria-live="polite">
                  <Mascot mood={feedback.correct ? 'xursand' : 'hayron'} size={64} />
                  <div className="bd-bubble mb-2 grow bg-bg! shadow-none!">
                    <span className={feedback.correct ? 'text-success-ink' : 'text-ink'}>{line}</span>{' '}
                    <span className="font-semibold text-ink-2">{feedback.explanation}</span>
                  </div>
                </div>
                <Button
                  fullWidth
                  className="mt-3"
                  onClick={onNext}
                  autoFocus
                  aria-label={isLast ? 'Natijani koʻrish' : 'Keyingi savolga oʻtish'}
                  rightIcon={<Icon name={isLast ? 'flag' : 'arrowR'} />}
                >
                  {isLast ? 'Natijani koʻrish' : 'Keyingi savolga oʻtish'}
                </Button>
              </>
            ) : (
              <p className="t-sm flex items-start gap-2 py-2 text-danger-ink" role="alert">
                <Icon name="alert" size={18} />
                Javobni yuborib boʻlmadi. Internetni tekshirib, javobni qayta tanlang.
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
