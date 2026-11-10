import { Link, Navigate, useLocation, useParams } from 'react-router';
import { useExam } from '../hooks/useExams';
import { ExamStatusChip } from '../components/ExamCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Mascot } from '@/components/shared/Mascot';
import { SUBJECTS, SubjectIcon } from '@/components/shared/subjects';
import { Section, StatTile, StatTiles, Steps, Sticky, TopBar } from '@/components/shared/design';

/** Dizayn: ScreenExams → “Imtihon tafsiloti”: 3 statistika plitasi, fanlar roʻyxati, 3 qadam, pastda yopishgan tugma. */
export default function ExamIntroPage() {
  const { examId = '' } = useParams();
  const { search } = useLocation(); // e.g. ?subject=iq from a subject card — kept when redirecting to the result
  const { exam, isPending, isError, error, refetch } = useExam(examId);

  if (isPending) {
    return (
      <div className="space-y-4 pt-14">
        <Skeleton className="h-32" />
        <Skeleton className="h-20" />
        <Skeleton className="h-56" />
      </div>
    );
  }
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;
  if (!exam)
    return (
      <EmptyState
        title="Imtihon topilmadi"
        description="Bu imtihon mavjud emas yoki hozir ochiq emas."
        action={
          <Link to="/" className={buttonClass('secondary')}>
            Bosh sahifaga
          </Link>
        }
      />
    );
  if (exam.status === 'in_progress' && exam.activeAttemptId) return <Navigate to={`/exam/attempt/${exam.activeAttemptId}`} replace />;
  if (exam.status === 'completed' && exam.resultId) return <Navigate to={`/results/${exam.resultId}${search}`} replace />;

  return (
    <div>
      <TopBar title="Imtihon" back="/exam" />

      <div className="row items-center! gap-3!">
        <div className="grow">
          <ExamStatusChip status={exam.status} />
          <h1 className="t-hero mt-2">{exam.title}</h1>
          <p className="t-sm muted mt-0.5">{exam.description}</p>
        </div>
        <Mascot mood="salom" size={84} />
      </div>

      <StatTiles className="mt-4">
        <StatTile icon="list" value={exam.totalQuestions} label="savol" />
        <StatTile icon="clock" value={exam.durationMinutes} label="daqiqa" tone="is-attn" />
        <StatTile icon="exam" value={exam.sections.length} label="fan" tone="is-star" />
      </StatTiles>

      <Section title="Imtihonda nimalar bor?" id="subjects-title">
        <ul className="bd-card bd-list px-4! py-0.5!">
          {exam.sections.map((s) => (
            <li key={s.subject} className={`bd-rowcard min-h-12 ${SUBJECTS[s.subject].tone}`}>
              <SubjectIcon subject={s.subject} />
              <span className="t-h3 grow">{SUBJECTS[s.subject].title}</span>
              <span className="t-sm muted tabular">{s.questionCount} ta savol</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Qanday ishlaydi?" id="how-title">
        <div className="bd-card px-4! py-3.5!">
          <Steps
            items={[
              { title: 'Javobni tanlang', text: 'Toʻgʻri deb oʻylagan javobingizni bosing — fikringizni oʻzgartirishingiz mumkin.' },
              { title: 'Savollar boʻylab harakatlaning', text: '“Keyingi” / “Oldingi” yoki savollar roʻyxati orqali.' },
              { title: 'Vaqt tugasa', text: 'Javoblar avtomatik saqlanadi va imtihon yakunlanadi.' },
            ]}
          />
        </div>
      </Section>

      <Sticky note={`Bir marta topshiriladi · ${exam.durationMinutes} daqiqa`}>
        <Link to={`/exam/${exam.id}/agreement`} className={buttonClass('primary', { fullWidth: true })}>
          Imtihonni boshlash
          <Icon name="arrowR" />
        </Link>
      </Sticky>
    </div>
  );
}
