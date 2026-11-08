import { useAnswerDailyQuestion, useDailyQuestion } from '@/features/brain-games/hooks/useGames';
import { Mascot } from '@/components/shared/Mascot';
import { Icon } from '@/components/ui/Icon';
import { Skeleton } from '@/components/ui/Skeleton';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';

/*
 * Dizayn: “Kun savoli” — krem karta, 2×2 javoblar.
 * Savol va toʻgʻri javob serverda: bitta javob qabul qilinadi (POST /games/daily-question/answer),
 * sahifa yangilansa ham natija koʻrinib turadi; toʻgʻri javob ⭐ ball beradi (header yangilanadi).
 */
export function DailyQuestion() {
  const { data, isPending, isError, refetch } = useDailyQuestion();
  const answer = useAnswerDailyQuestion();

  if (isPending) return <Skeleton className="h-52" />;
  if (isError || !data)
    return (
      <div className="bd-card bd-card--cream row gap-3!">
        <Mascot mood="hayron" size={48} />
        <p className="t-sm muted grow">Kun savolini yuklab boʻlmadi.</p>
        <button type="button" className="link" onClick={() => void refetch()}>
          Qayta urinish
        </button>
      </div>
    );

  const result = data.answer;
  const picked = result?.selectedOptionId ?? (answer.isPending ? answer.variables?.optionId : undefined);
  const right = result?.correct === true;

  return (
    <div className="bd-card bd-card--cream px-4! pt-3.5! pb-4!">
      <div className="row items-start! gap-2.5!">
        <div className="grow">
          <div className="t-over text-logic-ink">
            Kun savoli · +{data.points} ⭐
          </div>
          <p className="t-h3 mt-1">
            {data.question.prompt}
            <br />
            <span className="t-body muted">{data.question.sequence}</span>
          </p>
        </div>
        <Mascot mood={!result ? 'oylayapti' : right ? 'xursand' : 'hayron'} size={56} />
      </div>
      <div className="bd-answers mt-3" role="group" aria-label="Javob variantlari">
        {data.question.options.map((o) => {
          const isPicked = picked === o.id;
          const isRight = result?.correctOptionId === o.id;
          const isWrong = isPicked && result && !result.correct;
          const label = isRight ? `${o.label} — toʻgʻri javob` : isWrong ? `${o.label} — sening javobing, notoʻgʻri` : o.label;
          return (
            <button
              key={o.id}
              type="button"
              disabled={!!result || answer.isPending}
              aria-label={label}
              aria-pressed={isPicked}
              onClick={() => answer.mutate({ questionId: data.question.id, optionId: o.id })}
              className={cn('bd-answer', isRight && 'is-right', isWrong && 'is-wrong')}
            >
              {o.label}
              {isPicked && answer.isPending && <Spinner className="size-4 text-brand" />}
              {isRight && <Icon name="check" size={18} />}
              {isWrong && <Icon name="x" size={18} />}
            </button>
          );
        })}
      </div>
      <div role="status" aria-live="polite">
        {result && (
          <p className="t-sm mt-3">
            <b className={right ? 'text-success-ink' : 'text-ink'}>{right ? `Barakalla! +${result.pointsEarned} ⭐ ` : 'Hech gap emas, ertaga yana bir bor! '}</b>
            <span className="muted">{result.explanation}</span>
          </p>
        )}
        {answer.isError && <p className="t-sm mt-3 text-danger-ink">Javobni yuborib boʻlmadi. Internetni tekshirib, qayta tanla.</p>}
      </div>
    </div>
  );
}
