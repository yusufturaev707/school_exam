import { useId, useState } from 'react';
import { Navigate, useParams } from 'react-router';
import { useExam, useStartExam } from '../hooks/useExams';
import { Button } from '@/components/ui/Button';
import { Checkbox } from '@/components/ui/Checkbox';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { Mascot } from '@/components/shared/Mascot';
import { TopBar } from '@/components/shared/design';
import { ApiError } from '@/lib/http';

const RULES = [
  'Savollarni diqqat bilan oʻqing.',
  'Har bir savolga oʻzingiz mustaqil javob bering.',
  'Tushunmagan savolingiz boʻlsa, xotirjam qayta oʻqib chiqing.',
  'Javoblaringizni istalgan vaqtda oʻzgartirishingiz mumkin.',
  'Vaqt tugaganda javoblaringiz avtomatik saqlanadi va imtihon yakunlanadi.',
  'Eng muhimi, xotirjam boʻling va oʻz bilimingizga ishoning!',
];

function startErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'EXAM_NOT_AVAILABLE') return 'Imtihon hozir ochiq emas. Oʻqituvchingizdan soʻrab koʻring.';
    if (error.code === 'ALREADY_COMPLETED') return 'Siz bu imtihonni allaqachon topshirgansiz.';
    if (error.kind === 'network') return 'Internet aloqasi yoʻq. Ulanib, qayta urining.';
  }
  return 'Imtihonni boshlab boʻlmadi. Birozdan soʻng qayta urinib koʻring.';
}

/** The child-friendly "small agreement". Not a substitute for guardian consent, which is handled separately. */
export default function ExamAgreementPage() {
  const { examId = '' } = useParams();
  const { exam, isPending } = useExam(examId);
  const start = useStartExam();
  const [agreed, setAgreed] = useState(false);
  const checkboxId = useId();

  if (isPending) return <Skeleton className="mt-14 h-[480px]" />;
  if (exam?.status === 'in_progress' && exam.activeAttemptId) return <Navigate to={`/exam/attempt/${exam.activeAttemptId}`} replace />;
  if (!exam || exam.status === 'completed' || exam.status === 'unavailable') return <Navigate to={`/exam/${examId}`} replace />;

  return (
    <div>
      <TopBar title="Kichik kelishuv" back={`/exam/${examId}`} />
      <div className="bd-card relative overflow-hidden p-4!">
        <div className="absolute inset-x-0 top-0 h-14 bg-brand-soft" aria-hidden="true" />
        <div className="relative flex flex-col items-center text-center">
          <Mascot mood="xursand" size={104} />
          <h1 className="t-hero mt-2">Kichik kelishuvimiz</h1>
          <p className="t-sm muted mt-1">Imtihonni boshlashdan oldin bir nechta narsani kelishib olamiz:</p>
        </div>

        <ul className="relative mt-5 flex flex-col gap-2.5">
          {RULES.map((rule) => (
            <li key={rule} className="flex items-start gap-3">
              <span className="bd-tile is-brand mt-px size-6! rounded-full!" aria-hidden="true">
                <Icon name="check" size={14} />
              </span>
              <span className="t-body font-semibold">{rule}</span>
            </li>
          ))}
        </ul>

        <p className="bd-card--cream t-sm mt-5 rounded-[var(--radius-md)] p-3 text-logic-ink shadow-[inset_0_0_0_1px_var(--line)]">
          Esda tuting: bu imtihon bilimlaringizni yaxshiroq tushunish uchun oʻtkaziladi. Har bir natija yangi narsalarni oʻrganish imkoniyatidir.
        </p>

        <Checkbox id={checkboxId} className="mt-5" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} label="Men imtihon qoidalari bilan tanishdim." />

        {start.isError && (
          <p role="alert" className="t-sm mt-4 flex items-start gap-2 text-danger-ink">
            <Icon name="alert" size={18} />
            {startErrorMessage(start.error)}
          </p>
        )}

        <Button
          fullWidth
          className="mt-5"
          disabled={!agreed}
          loading={start.isPending}
          onClick={() => !start.isPending && start.mutate(exam.id)}
          rightIcon={<Icon name="arrowR" />}
          aria-describedby={!agreed ? `${checkboxId}-hint` : undefined}
        >
          Imtihonni boshlash
        </Button>
        {!agreed && (
          <p id={`${checkboxId}-hint`} className="t-sm muted mt-1 text-center">
            Boshlash uchun yuqoridagi belgini qoʻying.
          </p>
        )}
        <p className="t-xs faint mt-2 text-center">Vaqt faqat imtihon boshlangandan keyin hisoblanadi.</p>
      </div>
    </div>
  );
}
