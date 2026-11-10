import { useState } from 'react';
import { Link } from 'react-router';
import { useResult } from '../api/resultsApi';
import { overallHeadline } from '../utils/feedback';
import { ResultScore } from './ResultScore';
import { Modal } from '@/components/ui/Modal';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { StatTile, StatTiles } from '@/components/shared/design';

/** Imtihon yakunlangach oʻz-oʻzidan ochiladi: oʻquvchi balini darhol va katta koʻrinishda koʻradi. */
export function ExamScoreModal({ resultId }: { resultId: string }) {
  const { data } = useResult(resultId);
  const [open, setOpen] = useState(true);
  if (!data) return null;

  const { totals } = data;
  const headline = overallHeadline(totals.percent);

  return (
    <Modal
      open={open}
      onClose={() => setOpen(false)}
      variant="dialog"
      title={headline.title}
      description={headline.text}
      footer={
        <>
          <Link to="/" className={buttonClass('ghost', { fullWidth: true })}>
            <Icon name="home" />
            Bosh sahifaga
          </Link>
          <Link to={`/results/${resultId}`} replace className={buttonClass('primary', { fullWidth: true })}>
            Batafsil koʻrish
            <Icon name="arrowR" />
          </Link>
        </>
      }
    >
      <div className="bd-hero py-5!">
        <ResultScore totals={totals} examTitle={data.examTitle} />
      </div>
      <StatTiles className="mt-3">
        <StatTile center icon="check" value={totals.correct} label="toʻgʻri" tone="is-success" />
        <StatTile center icon="x" value={totals.incorrect} label="xato" tone="is-danger" />
        <StatTile center icon="help" value={totals.unanswered} label="javobsiz" tone="is-muted" />
      </StatTiles>
    </Modal>
  );
}
